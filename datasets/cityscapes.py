import os
import torch
import random
import numpy as np
import torch.nn.functional as F
from torch.utils import data
from PIL import Image
import torchvision.transforms as transforms
from torchvision.transforms import functional as TF

def cityscapesList(data_root):
    all_img_list = []
    data_root = os.path.join(data_root, 'leftImg8bit', 'val')
    # data_root = "/media/SSD2/wei/Dataset/SemanticSeg/cityscape/leftImg8bit/test/"
    citylist = os.listdir(data_root)
    
    for city in citylist:
        for img in os.listdir(os.path.join(data_root, city)):
            if img.split('.')[-1] == 'png':
                all_img_list.append(os.path.join(city, img))    # berlin/berlin_000000_000019_leftImg8bit.png
    
    return all_img_list

class cityscapesDataSet(data.Dataset):
    """
            original resolution at 2048x1024
    """
    def __init__(
            self,
            data_root,
            data_list,
            max_iters=None,
            num_classes=19,
            split="train",
            transform=None,
            ignore_label=255,
            debug=False,
    ):
        self.split = split
        self.NUM_CLASS = num_classes
        self.data_root = data_root
        self.data_list = []
        content = data_list
        #with open(data_list, "r") as handle:
        #    content = handle.readlines()
        
        # berlin/berlin_000000_000019_leftImg8bit.png
        # berlin_000000_000019_gtFine_labelIds.png

        for name in content:
            #name = fname.strip()
            self.data_list.append(
                {
                    "img": os.path.join(
                        self.data_root, "leftImg8bit/val/%s" % (name)
                    ),
                    "label": os.path.join(
                        self.data_root,
                        "gtFine/val/%s"
                        % (name.split("_leftImg8bit")[0]
                           + "_gtFine_labelIds.png",
                        ),
                    ),
                    "name": name,
                }
            )

        if max_iters is not None:
            self.data_list = self.data_list * int(np.ceil(float(max_iters) / len(self.data_list)))

        # --------------------------------------------------------------------------------
        # A list of all labels
        # --------------------------------------------------------------------------------

        # Please adapt the train IDs as appropriate for your approach.
        # Note that you might want to ignore labels with ID 255 during training.
        # Further note that the current train IDs are only a suggestion. You can use whatever you like.
        # Make sure to provide your results using the original IDs and not the training IDs.
        # Note that many IDs are ignored in evaluation and thus you never need to predict these!

        # labels = [
        #     #       name                     id    trainId   category            catId     hasInstances   ignoreInEval   color
        #     Label('unlabeled',                0,      255,    'void',             0,          False,          True,       (0, 0, 0)),
        #     Label('ego vehicle',              1,      255,    'void',             0,          False,          True,       (0, 0, 0)),
        #     Label('rectification border',     2,      255,    'void',             0,          False,          True,       (0, 0, 0)),
        #     Label('out of roi',               3,      255,    'void',             0,          False,          True,       (0, 0, 0)),
        #     Label('static',                   4,      255,    'void',             0,          False,          True,       (0, 0, 0)),
        #     Label('dynamic',                  5,      255,    'void',             0,          False,          True,       (111, 74, 0)),
        #     Label('ground',                   6,      255,    'void',             0,          False,          True,       (81, 0, 81)),
        #     Label('road',                     7,      0,      'flat',             1,          False,          False,      (128, 64, 128)),
        #     Label('sidewalk',                 8,      1,      'flat',             1,          False,          False,      (244, 35, 232)),
        #     Label('parking',                  9,      255,    'flat',             1,          False,          True,       (250, 170, 160)),
        #     Label('rail track',               10,     255,    'flat',             1,          False,          True,       (230, 150, 140)),
        #     Label('building',                 11,     2,      'construction',     2,          False,          False,      (70, 70, 70)),
        #     Label('wall',                     12,     3,      'construction',     2,          False,          False,      (102, 102, 156)),
        #     Label('fence',                    13,     4,      'construction',     2,          False,          False,      (190, 153, 153)),
        #     Label('guard rail',               14,     255,    'construction',     2,          False,          True,       (180, 165, 180)),
        #     Label('bridge',                   15,     255,    'construction',     2,          False,          True,       (150, 100, 100)),
        #     Label('tunnel',                   16,     255,    'construction',     2,          False,          True,       (150, 120, 90)),
        #     Label('pole',                     17,     5,      'object',           3,          False,          False,      (153, 153, 153)),
        #     Label('polegroup',                18,     255,    'object',           3,          False,          True,       (153, 153, 153)),
        #     Label('traffic light',            19,     6,      'object',           3,          False,          False,      (250, 170, 30)),
        #     Label('traffic sign',             20,     7,      'object',           3,          False,          False,      (220, 220, 0)),
        #     Label('vegetation',               21,     8,      'nature',           4,          False,          False,      (107, 142, 35)),
        #     Label('terrain',                  22,     9,      'nature',           4,          False,          False,      (152, 251, 152)),
        #     Label('sky',                      23,     10,     'sky',              5,          False,          False,      (70, 130, 180)),
        #     Label('person',                   24,     11,     'human',            6,          True,           False,      (220, 20, 60)),
        #     Label('rider',                    25,     12,     'human',            6,          True,           False,      (255, 0, 0)),
        #     Label('car',                      26,     13,     'vehicle',          7,          True,           False,      (0, 0, 142)),
        #     Label('truck',                    27,     14,     'vehicle',          7,          True,           False,      (0, 0, 70)),
        #     Label('bus',                      28,     15,     'vehicle',          7,          True,           False,      (0, 60, 100)),
        #     Label('caravan',                  29,     255,    'vehicle',          7,          True,           True,       (0, 0, 90)),
        #     Label('trailer',                  30,     255,    'vehicle',          7,          True,           True,       (0, 0, 110)),
        #     Label('train',                    31,     16,     'vehicle',          7,          True,           False,      (0, 80, 100)),
        #     Label('motorcycle',               32,     17,     'vehicle',          7,          True,           False,      (0, 0, 230)),
        #     Label('bicycle',                  33,     18,     'vehicle',          7,          True,           False,      (119, 11, 32)),
        #     Label('license plate',             -1,    -1,     'vehicle',          7,          False,          True,       (0, 0, 142)),
        # ]

        # GTA5, Synscapes, cross-city
        self.id_to_trainid = {
            7: 0,
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
            33: 18,
        }
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
            18: "bicycle",
        }
        if self.NUM_CLASS == 16:  # SYNTHIA
            self.id_to_trainid = {
                7: 0,
                8: 1,
                11: 2,
                12: 3,
                13: 4,
                17: 5,
                19: 6,
                20: 7,
                21: 8,
                23: 9,
                24: 10,
                25: 11,
                26: 12,
                28: 13,
                32: 14,
                33: 15,
            }
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
                9: "sky",
                10: "person",
                11: "rider",
                12: "car",
                13: "bus",
                14: "motocycle",
                15: "bicycle",
            }
        #self.transform = transform

        self.ignore_label = ignore_label

        self.debug = debug
        
        transformList = [transforms.ToTensor(),
                         transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])]
                             
        self.transform = transforms.Compose(transformList)

    def __len__(self):
        return len(self.data_list)

    def __getitem__(self, index):
        if self.debug:
            index = 0
        datafiles = self.data_list[index]

        image = Image.open(datafiles["img"]).convert('RGB')
        label = Image.open(datafiles["label"])
        name = datafiles["name"]
        
        # Cropping 
        #w, h = image.size
        #th, tw = 512, 1024
        
        #x1 = random.randint(0, w-tw)
        #y1 = random.randint(0, h-th)

        #image = image.crop((x1, y1, x1 + tw, y1 + th))
        #label = label.crop((x1, y1, x1 + tw, y1 + th))
        
        label = np.array(label, dtype=np.float32)

        # re-assign labels to match the format of Cityscapes
        label_copy = self.ignore_label * np.ones(label.shape, dtype=np.float32)
        for k, v in self.id_to_trainid.items():
            #print(k, v)
            label_copy[label == k] = v
        # for k in self.trainid2name.keys():
        #     label_copy[label == k] = k
        label = Image.fromarray(label_copy)

        image = self.transform(image)
        #label = torch.from_numpy(label)
        label = TF.to_tensor(label).squeeze()
        
        return image, label, name
