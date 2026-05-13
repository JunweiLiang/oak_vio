# note by junwei
# repo: https://github.com/JunweiLiang/oak_vio

### 测试
```
    0. 安装
        $ conda create -n oak python=3.10
        $ conda activate oak
        $ pip install spectacularAI[full]

        # 设置udev permission
        $ echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="03e7", MODE="0666"' | sudo tee /etc/udev/rules.d/80-movidius.rules
        $ sudo udevadm control --reload-rules && sudo udevadm trigger


    1. mapping

        1. 官方mapping script

            (oak) junweil@office-precognition:~/projects/oak_vio$ python python/oak/mapping_visu.py

            开启后马上开始SLAM，可以看到3D point cloud办公室能重建出来，移动相机，pose基本都能和地图对应
```
