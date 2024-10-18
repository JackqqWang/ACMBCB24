
import numpy as np
import matplotlib.pyplot as plt
from sampling import iid
from sampling import *

from torchvision import datasets, transforms
import numpy as np
import matplotlib.pyplot as plt
from datasets import load_dataset, Dataset, DatasetDict
from sampling import iid
from sampling import sst2_noniid, ag_news_noniid
from torchvision import datasets, transforms
from torchvision.datasets import ImageFolder
from PIL import Image
from tqdm import tqdm
import copy
import torch
from torch.nn.functional import kl_div, softmax, log_softmax, cross_entropy

from torch.utils.data import ConcatDataset
from FLamby.flamby.datasets.fed_isic2019 import FedIsic2019
def exp_details(args):
    print('\nExperimental details:')
    
    
    
    print(f'    Communication Rounds   : {args.communication_round}\n')
    print(f'    Number of users        : {args.num_users}')
    print(f'    Fraction of users  : {args.frac}')
    print(f'    Dataset      : {args.dataset}')
    print(f'    Num of classes: {args.num_classes}')
    


    print('    Federated parameters:')
    if args.iid:
        print('    IID')
    else:
        print('    Non-IID')
    
    
    
    return


def get_dataset(args):
    
    val_key = 'test' if args.dataset == 'ag_news' else 'validation'

    


    if args.dataset == 'ISIC':
        train_dataset_lst=[]
        seperate_mark_list=[0]
        for i in range(6):
            dst=FedIsic2019(center=i, train=True)
            train_dataset_lst.append(dst)
            seperate_mark_list.append(len(dst)+seperate_mark_list[-1])
        train_set = ConcatDataset(train_dataset_lst)
        test_dataset_lst = []
        seperate_mark_list_test = [0]
        for i in range(6):
            dst = FedIsic2019(center=i, train=False)
            test_dataset_lst.append(dst)
            seperate_mark_list_test.append(len(dst) + seperate_mark_list_test[-1])
        test_set = ConcatDataset(test_dataset_lst)
        user_groups={}
        
        
        for i in range(6):
            user_groups[i]=[[i for i in range(seperate_mark_list[i],seperate_mark_list[i+1])],[i for i in range(seperate_mark_list_test[i],seperate_mark_list_test[i+1])]]
    
        for i in range(3):
            user_groups[i] = [[i for i in range(seperate_mark_list[i], seperate_mark_list[i + 1])],
                            [i for i in range(seperate_mark_list_test[i], seperate_mark_list_test[i + 1])]]

        num_classes = 8



    elif args.dataset == 'cifar100':
        data_dir = './data/cifar100/'
        transform = transforms.Compose([
            transforms.Resize((32, 32)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
        ])
        train_set = datasets.CIFAR100(data_dir, train=True, download=True, transform=transform)
        test_set = datasets.CIFAR100(data_dir, train=False, download=True, transform=transform)
        num_classes = 100
    elif args.dataset == 'cifar10':
        data_dir = './data/cifar10/'
        transform = transforms.Compose([
            transforms.Resize((32, 32)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
        ])
        train_set = datasets.CIFAR10(data_dir, train=True, download=True, transform=transform)
        test_set = datasets.CIFAR10(data_dir, train=False, download=True, transform=transform)
        num_classes = 10

    elif args.dataset == 'fmnist':
        data_dir = './data/fmnist/'
        transform=transforms.Compose([
            transforms.Resize((32, 32)),

            transforms.ToTensor(),
            transforms.Normalize((0.1307,), (0.3081,)),
        ])
        train_set = datasets.FashionMNIST(data_dir, train=True, download=True, transform=transform)
        test_set = datasets.FashionMNIST(data_dir, train=False, download=True, transform=transform)
        num_classes = 10
        
    else:
        exit(f'Error: no {args.dataset} dataset')




    if args.dataset == 'ISIC':
            user_groups = user_groups
  
        
        
        
            
        
            

    return train_set, test_set, num_classes, user_groups


def average_weights(w):
    """
    Returns the average of the weights.
    """
    w_avg = copy.deepcopy(w[0])
    for key in w_avg.keys():
        for i in range(1, len(w)):
            w_avg[key] += w[i][key]
        w_avg[key] = torch.div(w_avg[key], len(w))
    return w_avg


def cal_sim_set(input_list1, input_list2):
    """
    
    """
    sim_sum = 0
    for i in range(len(input_list1)):
        sim_sum = sim_sum + len(set(input_list1[i]).intersection(set(input_list2[i]))) / len(set(input_list1[i]).union(set(input_list2[i])))
    sim_avg = sim_sum / len(input_list1)
        
    return sim_avg



def cal_consensus(input_list_small, input_list_large):

    consensus_sum = 0
    for i in range(len(input_list_small)):
        if len(input_list_large[i]) <= len(input_list_small[i]):
            consensus_sum = consensus_sum + len(set(input_list_large[i]).intersection(set(input_list_small[i])))\
                                               /  len(set(input_list_large[i]).union(set(input_list_small[i])))
        else:
            consensus_sum = consensus_sum + len(set(input_list_small[i]).intersection(set(input_list_large[i])))/ len(set(input_list_small[i]))

    consensus_avg = consensus_sum / len(input_list_small)
    return consensus_avg


def cal_lambda(train_acc_change,args):
    if train_acc_change>=0:
        return args.small_lamda
    else:
        if args.lambda_function == 'fenduan_linear':

            return -(1-args.small_lamda)* train_acc_change + args.small_lamda

        elif args.lambda_function == 'fenduan_nonliner':

            result = (1-args.small_lamda) * train_acc_change * train_acc_change + args.small_lamda
            return result
        elif args.lambda_function == 'fixed':
            return args.small_lamda
    
        
   
def weighted_CE(logits, targets, sample_weights):

    sample_weights = sample_weights / sample_weights.sum()
    
    loss = torch.nn.CrossEntropyLoss(reduction='none')(logits, targets)
    loss *= sample_weights

    return loss.mean()

