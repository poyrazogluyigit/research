#!/usr/bin/env python
# coding: utf-8


import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim import lr_scheduler
import torch.backends.cudnn as cudnn
import numpy as np
import torchvision
from torchvision import datasets, models, transforms
import matplotlib.pyplot as plt
import time
import os
from PIL import Image
from tempfile import TemporaryDirectory

cudnn.benchmark = True
plt.ion()   # interactive mode

# Data augmentation and normalization for training
# Just normalization for validation
data_transforms = {
    'train': transforms.Compose([
        transforms.Resize(224),
        transforms.ToTensor(),
        transforms.Normalize([0.36883902,0.36883902,0.36883902], 
                             [0.31923532,0.31923532,0.31923532]
                            )
    ]),
    'val': transforms.Compose([
        transforms.Resize(224),
        transforms.ToTensor(),
        transforms.Normalize([0.34951498,0.34951498,0.34951498], 
                             [0.31069174,0.31069174,0.31069174]
                            )
    ]),
}

data_dir = '/blue/fl-poly/oguzhan/radimagenet/data/img-reorganized/FLAIR'

image_datasets = {x: datasets.ImageFolder(os.path.join(data_dir, x),
                                          data_transforms[x])
                  for x in ['train', 'val']}

#image_datasets = {x: datasets.ImageFolder(os.path.join(data_dir, x), data_transforms[x]) for x in ['train', 'val']}
dataloaders = {x: torch.utils.data.DataLoader(image_datasets[x], batch_size=4,
                                             shuffle=True, num_workers=1)
              for x in ['train', 'val']}
dataset_sizes = {x: len(image_datasets[x]) for x in ['train', 'val']}
class_names = image_datasets['train'].classes

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")



def train_model(model, criterion, optimizer, scheduler, num_epochs=25):
    since = time.time()

    # Create a temporary directory to save training checkpoints
    with TemporaryDirectory() as tempdir:
        best_model_params_path = os.path.join(tempdir, 'best_model_params.pt')
    
        torch.save(model.state_dict(), best_model_params_path)
        best_acc = 0.0
        print(f'Starting to train for {num_epochs} epocs')

        for epoch in range(num_epochs):
            train_acc = 0.0
            train_loss = 0.0
            val_acc = 0.0
            val_loss = 0.0
            
            # Each epoch has a training and validation phase
            for phase in ['train', 'val']:
                if phase == 'train':
                    model.train()  # Set model to training mode
                else:
                    model.eval()   # Set model to evaluate mode

                running_loss = 0.0
                running_corrects = 0

                # Iterate over data.
                for inputs, labels in dataloaders[phase]:
                    inputs = inputs.to(device)
                    labels = labels.to(device)

                    # zero the parameter gradients
                    optimizer.zero_grad()

                    # forward
                    # track history if only in train
                    with torch.set_grad_enabled(phase == 'train'):
                        outputs = model(inputs)
                        _, preds = torch.max(outputs, 1)
                        loss = criterion(outputs, labels)

                        # backward + optimize only if in training phase
                        if phase == 'train':
                            loss.backward()
                            optimizer.step()

                    # statistics
                    running_loss += loss.item() * inputs.size(0)
                    running_corrects += torch.sum(preds == labels.data)
                if phase == 'train':
                    scheduler.step()

                epoch_loss = running_loss / dataset_sizes[phase]
                epoch_acc = running_corrects.double() / dataset_sizes[phase]

                if phase == 'train':
                    train_acc = epoch_acc
                    train_loss = epoch_loss
                else:
                    val_acc = epoch_acc
                    val_loss = epoch_loss
                    
                #print(f'{phase} Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}')

                # deep copy the model
                if phase == 'val' and epoch_acc > best_acc:
                    best_acc = epoch_acc
                    torch.save(model.state_dict(), best_model_params_path)
                    
            print(f'{epoch}: val_loss: {val_loss:.3f} val_acc: {val_acc:.3f} train_loss: {train_loss:.3f} train_acc: {train_acc:.3f}')

        time_elapsed = time.time() - since
        print(f'Training complete in {time_elapsed // 60:.0f}m {time_elapsed % 60:.0f}s')
        print(f'Best val Acc: {best_acc:4f}')

        # load best model weights
        model.load_state_dict(torch.load(best_model_params_path))
    return model


num_classes = 2

currentPreTrainedModel = 'resnet18'
model_ft = models.resnet18(weights='IMAGENET1K_V1')
num_input_ftrs = model_ft.fc.in_features
model_ft.fc = nn.Linear(num_input_ftrs, num_classes)


#currentPreTrainedModel = 'efficientnet_b0'
#model_ft = models.efficientnet_b0(weights='IMAGENET1K_V1')
#num_input_ftrs = model_ft.classifier[1].in_features
#model_ft.classifier = nn.Sequential(
#            nn.Dropout(p=0.2, inplace=True),
#            nn.Linear(num_input_ftrs, num_classes),
#)

model_ft = model_ft.to(device)
criterion = nn.CrossEntropyLoss()

print(f'PRE-TRAINED Model: {currentPreTrainedModel}')
print('HYPERPARAMETERS:')
# Observe that all parameters are being optimized
#optimizer_ft = optim.SGD(model_ft.parameters(), lr=0.0001, momentum=0.9)
#print('optimizer_ft = optim.SGD(model_ft.parameters(), lr=0.0001, momentum=0.9)')

optimizer_ft = optim.Adam(model_ft.parameters(), lr=0.001)
print('optimizer_ft = optim.Adam(model_ft.parameters(), lr=0.001)')

# Decay LR by a factor of 0.1 every 7 epochs
exp_lr_scheduler = lr_scheduler.StepLR(optimizer_ft, step_size=7, gamma=0.1)
print('exp_lr_scheduler = lr_scheduler.StepLR(optimizer_ft, step_size=7, gamma=0.1)')

model_ft = train_model(model_ft, criterion, optimizer_ft, exp_lr_scheduler, num_epochs=30)

