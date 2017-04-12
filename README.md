# vm_manager
Simple tool to start/stop your vm and automatically connect to it with xfreerdp client. Useful for linux users who need quick access to windows-only tools.

vm_manager.py - script file
vm_manager.conf - configuration file

Recommended to use with desktop launcher.

## Requirements
* dependencies
    * Python 3.5 and above (not tested with other versions)
    * VirtuaBox and VBoxManage tool available as /usr/bin/VBoxManage
    * xfreerdp client available as /usr/bin/xfreerdp
* ready to use VM with configured
    * RDP server
    * NAT vm network and RDP port forwarding
    * username and password

## Configuration file

vm_manager.conf is ini-like configuration file. Sould always be placed near vm_manager.py file.

All configuration options are mandatory. Current version doesn't have default settings for now.

### Configuration options

**Section "virtualbox"**  
`vmname = target_vm_list`  
Target vm name to start/stop.

**Section "save_timeout"**  
Timeout settings to delay vm save operation on rdp connection close.    

`timeout = 60`  
Timeout value in minutes.

`days = 1,2,3,4,5`  
Week days when to use timeout separated by comma (1 = monday).
  
`hours_start = 9:00`  
Start hours when to use timeout.

`hours_end = 19:00`  
End hours when to use timeout. If timeout ends later, vm will be saved at this time.

**Section "rdp"**  
Defines xfreerdp connection options.  

`host = localhost`  
Hostname or IP address of target vm.

`port = 53389`  
RDP port of target vm.

`username = admin`  
`password = password`  
RDP credentials.
  
`options = /clipboard /f`  
Additional xfreerdp command line options.

**Section "logging"**  
`level = DEBUG`  
Standard output logging level. Available levels: DEBUG, INFO, ERROR, CRITICAL.
