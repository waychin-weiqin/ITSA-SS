import os
import os.path as osp
import numpy as np
from torch.utils import data
from PIL import Image, ImageFile
import pickle
import torchvision.transforms as transforms
from torchvision.transforms import functional as F
import random 
import torch

ImageFile.LOAD_TRUNCATED_IMAGES = True


def gtaList(data_root):
    all_img_list = [img for img in os.listdir(os.path.join(data_root, "images")) if img.split('.')[-1] == 'png']

    train_list = all_img_list[:23466]
    test_list = all_img_list[23466:]
    
    return train_list, test_list
    

class GTAVDataSet(data.Dataset):
    """
        original resolution at 1914x1024
    """
    def __init__(self,
                 data_root,
                 data_list,
                 max_iters=None,
                 num_classes=19,
                 transform=None,
                 train=True,
                 ignore_label=255,
                 debug=False, 
                 augment=False):
        self.train = train
        self.NUM_CLASS = num_classes
        self.data_root = data_root
        self.data_list = []
        #with open(data_list, "r") as handle:
        #    content = handle.readlines()
        #self.img_ids = [i_id.strip() for i_id in content]
        self.img_ids = data_list
        self.augment = augment

        if max_iters is not None:
            self.label_to_file, self.file_to_label = pickle.load(open(osp.join(data_root, "gtav_label_info.p"), "rb"))
            self.img_ids = []
            SUB_EPOCH_SIZE = 3000
            tmp_list = []
            ind = dict()
            for i in range(self.NUM_CLASS):
                ind[i] = 0
            for e in range(int(max_iters / SUB_EPOCH_SIZE) + 1):
                cur_class_dist = np.zeros(self.NUM_CLASS)
                for i in range(SUB_EPOCH_SIZE):
                    if cur_class_dist.sum() == 0:
                        dist1 = cur_class_dist.copy()
                    else:
                        dist1 = cur_class_dist / cur_class_dist.sum()
                    w = 1 / np.log(1 + 1e-2 + dist1)
                    w = w / w.sum()
                    c = np.random.choice(self.NUM_CLASS, p=w)

                    if ind[c] > (len(self.label_to_file[c]) - 1):
                        np.random.shuffle(self.label_to_file[c])
                        ind[c] = ind[c] % (len(self.label_to_file[c]) - 1)

                    c_file = self.label_to_file[c][ind[c]]
                    tmp_list.append(c_file)
                    ind[c] = ind[c] + 1
                    cur_class_dist[self.file_to_label[c_file]] += 1

            self.img_ids = tmp_list

        for name in self.img_ids:
            self.data_list.append(
                {
                    "img": os.path.join(self.data_root, "images/%s" % name),
                    "label": os.path.join(self.data_root, "labels/%s" % name),
                    "name": name,
                }
            )

        if max_iters is not None:
            self.data_list = self.data_list * int(np.ceil(float(max_iters) / len(self.data_list)))

        self.id_to_trainid = {7: 0,
                              8: 1,
                              11: 2,
                              12: 3,
                              13: 4,
                              17: 5,
                              19: 6,
                              20: 7,
                              21: 8,
                              22: 9,
                              23: 10,
                              24: 11,
                              25: 12,
                              26: 13,
                              27: 14,
                              28: 15,
                              31: 16,
                              32: 17,
                              33: 18}
        self.trainid2name = {
            0: "road",
            1: "sidewalk",
            2: "building",
            3: "wall",
            4: "fence",
            5: "pole",
            6: "light",
            7: "sign",
            8: "vegetation",
            9: "terrain",
            10: "sky",
            11: "person",
            12: "rider",
            13: "car",
            14: "truck",
            15: "bus",
            16: "train",
            17: "motocycle",
            18: "bicycle"
        }
        self.ignore_label = ignore_label
        self.debug = debug
        
        if self.train:                             
            if self.augment:
                transformList = [transforms.GaussianBlur(kernel_size=[3, 3]),
                                 transforms.RandomGrayscale(p=0.33),
                                 transforms.ColorJitter(
                                         brightness=[0.4,2.0],
                                         contrast=[0.5,1.5],
                                         saturation=[0.5,1.5]), 
                                 transforms.ToTensor(),
                                 transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])]
            else:
                transformList = [transforms.ToTensor(),
                             transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])]
                             
        else:
            transformList = [transforms.ToTensor(),
                             transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])]
                             
        self.transform = transforms.Compose(transformList)


    def __len__(self):
        return len(self.data_list)
        
    def add_noise(self, img):
        img = transforms.ToTensor()(img)
        
        img = img + torch.randn_like(img)*0.01
        img = torch.clip(img, 0, 1)
        
        img = transforms.ToPILImage()(img)
        
        return img 

    def __getitem__(self, index):
        if self.debug:
            index = 0
        datafiles = self.data_list[index]

        image = Image.open(datafiles["img"]).convert('RGB')
        label = np.array(Image.open(datafiles["label"]), dtype=np.float32)
        name = datafiles["name"]

        # re-assign labels to match the format of Cityscapes
        label_copy = self.ignore_label * np.ones(label.shape, dtype=np.float32)
        for k, v in self.id_to_trainid.items():
            label_copy[label == k] = v
        label = Image.fromarray(label_copy)
        
        # Cropping 
        w, h = image.size
        th, tw = 512, 1024
        
        x1 = random.randint(0, w-tw)
        y1 = random.randint(0, h-th)

        image = image.crop((x1, y1, x1 + tw, y1 + th))
        label = label.crop((x1, y1, x1 + tw, y1 + th))
        
        if self.augment:
            gamma_scale = np.random.uniform(0.8, 1.2)
            image = F.adjust_gamma(image, gamma_scale)
            #image = self.add_noise(image)
        
        image = self.transform(image)
        label = F.to_tensor(label).squeeze()
        
        return image, label, name
