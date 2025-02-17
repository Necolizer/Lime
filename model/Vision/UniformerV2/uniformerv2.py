#!/usr/bin/env python
import json
import torch
import torch.nn as nn

import model.Vision.UniformerV2.uniformerv2_model as model
# import uniformerv2_model as model

class Uniformerv2(nn.Module):
    def __init__(self, cfg):
        super().__init__()

        self.cfg = cfg

        use_checkpoint = cfg.MODEL.USE_CHECKPOINT
        checkpoint_num = cfg.MODEL.CHECKPOINT_NUM
        num_classes = cfg.MODEL.NUM_CLASSES 
        t_size = cfg.DATA.NUM_FRAMES

        backbone = cfg.UNIFORMERV2.BACKBONE
        n_layers = cfg.UNIFORMERV2.N_LAYERS
        n_dim = cfg.UNIFORMERV2.N_DIM
        n_head = cfg.UNIFORMERV2.N_HEAD
        mlp_factor = cfg.UNIFORMERV2.MLP_FACTOR
        backbone_drop_path_rate = cfg.UNIFORMERV2.BACKBONE_DROP_PATH_RATE
        drop_path_rate = cfg.UNIFORMERV2.DROP_PATH_RATE
        mlp_dropout = cfg.UNIFORMERV2.MLP_DROPOUT
        cls_dropout = cfg.UNIFORMERV2.CLS_DROPOUT
        return_list = cfg.UNIFORMERV2.RETURN_LIST

        temporal_downsample = cfg.UNIFORMERV2.TEMPORAL_DOWNSAMPLE
        dw_reduction = cfg.UNIFORMERV2.DW_REDUCTION
        no_lmhra = cfg.UNIFORMERV2.NO_LMHRA
        double_lmhra = cfg.UNIFORMERV2.DOUBLE_LMHRA

        frozen = cfg.UNIFORMERV2.FROZEN

        # pre-trained from CLIP
        self.backbone = model.__dict__[backbone](
            pretrained=False,
            use_checkpoint=use_checkpoint,
            checkpoint_num=checkpoint_num,
            t_size=t_size,
            dw_reduction=dw_reduction,
            backbone_drop_path_rate=backbone_drop_path_rate, 
            temporal_downsample=temporal_downsample,
            no_lmhra=no_lmhra,
            double_lmhra=double_lmhra,
            return_list=return_list, 
            n_layers=n_layers, 
            n_dim=n_dim, 
            n_head=n_head, 
            mlp_factor=mlp_factor, 
            drop_path_rate=drop_path_rate, 
            mlp_dropout=mlp_dropout, 
            cls_dropout=cls_dropout, 
            num_classes=num_classes,
            frozen=frozen,
        )

        if cfg.UNIFORMERV2.PRETRAIN != '':
            # Load Kineti-700 pretrained model
            state_dict = torch.load(cfg.UNIFORMERV2.PRETRAIN, map_location='cpu')
            if cfg.UNIFORMERV2.DELETE_SPECIAL_HEAD and state_dict['backbone.transformer.proj.2.weight'].shape[0] != num_classes:
                del state_dict['backbone.transformer.proj.2.weight']
                del state_dict['backbone.transformer.proj.2.bias']
            elif not cfg.UNIFORMERV2.DELETE_SPECIAL_HEAD:
                if num_classes == 400 or state_dict['backbone.transformer.proj.2.weight'].shape[0] == num_classes:
                    state_dict['backbone.transformer.proj.2.weight'] = state_dict['backbone.transformer.proj.2.weight'][:num_classes]
                    state_dict['backbone.transformer.proj.2.bias'] = state_dict['backbone.transformer.proj.2.bias'][:num_classes]
                else:
                    map_path = f'./data_list/k710/label_mixto{num_classes}.json'
                    with open(map_path) as f:
                        label_map = json.load(f)
                    state_dict['backbone.transformer.proj.2.weight'] = state_dict['backbone.transformer.proj.2.weight'][label_map]
                    state_dict['backbone.transformer.proj.2.bias'] = state_dict['backbone.transformer.proj.2.bias'][label_map]
            self.load_state_dict(state_dict, strict=False)

        if frozen:
            backbone_list = [
                # Backbone
                'conv1', 'class_embedding', 'positional_embedding', 'ln_pre', 'transformer.resblocks'
            ]
            for name, p in self.backbone.named_parameters():
                flag = False
                for module in backbone_list:
                    if module in name:
                        flag = True
                        break
                if flag:
                    p.requires_grad = False

    def forward(self, x):
        # x = x[0]
        output = self.backbone(x)

        return output
    
    # def forward_feature(self, x):
    #     output = self.backbone.forward_feature(x)
    #     return output

if __name__ == '__main__':
    import numpy as np

    seed = 4217
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

    import yaml
    from dotmap import DotMap

    with open(r'./config.yaml', 'r') as f:
        cfg = yaml.load(f, yaml.FullLoader)

    m = Uniformerv2(
        DotMap(cfg)
    )

    x = torch.rand((1, 3, 8, 224, 224))

    out = m(x)
    print(out.shape)

    out = m.forward_feature(x)
    print(out.shape)