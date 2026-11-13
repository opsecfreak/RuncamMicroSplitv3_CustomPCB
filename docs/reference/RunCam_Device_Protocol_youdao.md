# RunCam Device Protocol

## 1. Read camera information
Command | ID |Function | Device feature requirements
--- | --- |--- | ---
RCDEVICE_PROTOCOL_COMMAND_GET_DEVICE_INFO | 0x00 | Read the basic information of the camera, such as firmware version, device type, protocol version| Null

##### Request packet structure, the length is 3 bytes：
Header | Command ID | crc8
--- | --- | ---  
0xCC | 0x00 | Check code

##### Response packet structure
Field | Value | Type 
---|--- | ---
Header | 0xCC | uint8_t
Protocol Version | Protocol version | uint8_t
Feature | Device feature | uint16_t, Refer to the Feature section for details
crc8 | Check code| uint8_t

#### Feature
Features | Value | Description
--- | --- | --- 
RCDEVICE_PROTOCOL_FEATURE_SIMULATE_POWER_BUTTON | 1 << 0 | Simulation Click the power button
RCDEVICE_PROTOCOL_FEATURE_SIMULATE_WIFI_BUTTON | 1 << 1 | Simulation Click the Wi-Fi button
RCDEVICE_PROTOCOL_FEATURE_CHANGE_MODE | 1 << 2 | Switch the device operating mode
RCDEVICE_PROTOCOL_FEATURE_SIMULATE_5_KEY_OSD_CABLE | 1 << 3 | Simulation 5-key OSD remote control
RCDEVICE_PROTOCOL_FEATURE_DEVICE_SETTINGS_ACCESS | 1 << 4 | Support access to device settings
RCDEVICE_PROTOCOL_FEATURE_DISPLAYP_PORT | 1 << 5 | The device is identified as a DisplayPort device by flying controller and receives the OSD data display from the flight controller
RCDEVICE_PROTOCOL_FEATURE_START_RECORDING | 1 << 6 | Control the camera to start recording video
RCDEVICE_PROTOCOL_FEATURE_STOP_RECORDING  | 1 << 7 | Control the camera to stop recording video
## 2. Camera control
Command| ID |Function | Camera feature requirements
--- | --- |--- | ---
RCDEVICE_PROTOCOL_COMMAND_CAMERA_CONTROL | 0x01 | Camera control，For example: through this instruction, send an instruction to simulate the actions of power button to the camera |  RCDEVICE_PROTOCOL_FEATURE_SIMULATE_POWER_BUTTON, RCDEVICE_PROTOCOL_FEATURE_SIMULATE_WIFI_BUTTON, RCDEVICE_PROTOCOL_FEATURE_CHANGE_MODE, RCDEVICE_PROTOCOL_FEATURE_START_RECORDING, RCDEVICE_PROTOCOL_FEATURE_STOP_RECORDING

###### Request packet structure, the length is fixed to 4 bytes：
Header | Command ID | Action ID  | crc8
--- | --- | --- | --- 
0xCC | 0x01 | Please refer to the 'Action' section for specific values | Check code

###### Action
Action | Value | Description
--- | --- | --- 
RCDEVICE_PROTOCOL_SIMULATE_WIFI_BTN | 0x00 | Simulation Click the Wi-Fi button
RCDEVICE_PROTOCOL_SIMULATE_POWER_BTN | 0x01 | Simulation Click the Power button
RCDEVICE_PROTOCOL_CHANGE_MODE | 0x02 | Switch the camera mode
RCDEVICE_PROTOCOL_CHANGE_START_RECORDING | 0x03 | Control the camera to start recording
RCDEVICE_PROTOCOL_CHANGE_STOP_RECORDING | 0x04 | Control the camera to stop recording


## 3.Simulate Press command of the 5 key remote control
Command | ID |Function| Camera feature requirements
--- | --- |--- | ---
RCDEVICE_PROTOCOL_COMMAND_5KEY_SIMULATION_PRESS | 0x02 | Send the Press event of the 5 key remote control to the camera | RCDEVICE_PROTOCOL_FEATURE_SIMULATE_5_KEY_OSD_CABLE

###### Request packet structure, the length is fixed to 4 bytes：
Header | Command ID | Action ID | crc8
--- | --- | --- | ---
0xCC | 0x02 | Refer to the Action section for specific values| Check code

###### Action
Action | Value |Description
--- | --- | --- 
RCDEVICE_PROTOCOL_5KEY_SIMULATION_SET   | 0x01 | Simulate the confirmation key of the 5 key remote control
RCDEVICE_PROTOCOL_5KEY_SIMULATION_LEFT  | 0x02 | Simulate the left key of the 5 key remote control
RCDEVICE_PROTOCOL_5KEY_SIMULATION_RIGHT | 0x03 | Simulate the right key of the 5 key remote control
RCDEVICE_PROTOCOL_5KEY_SIMULATION_UP    | 0x04 | Simulate the up key of the 5 key remote control
RCDEVICE_PROTOCOL_5KEY_SIMULATION_DOWN  | 0x05 | Simulate the down key of the 5 key remote control

###### Response packet structure, the length is fixed to 2 bytes：
Header | crc8
--- | ---
0xCC | Check code


## 4.Simulate Release command of the 5 key remote control 
Command | ID |Function | Camera feature requirements
--- | --- |--- | ---
RCDEVICE_PROTOCOL_COMMAND_5KEY_SIMULATION_RELEASE | 0x03 | Send the Release event of the 5 key remotre control to the camera | RCDEVICE_PROTOCOL_FEATURE_SIMULATE_5_KEY_OSD_CABLE

###### Request packet structure, the length is fixed to 3 bytes：
Header | Command ID | crc8
--- | --- | --- | ---
0xCC | 0x03 | Check code

###### Response packet structure, the length is fixed to 2 bytes：
Header | crc8
--- | ---
0xCC | Check code


## 5.Simulate handshake/disconnection command
Command | ID |Function | Camera feature requirements
--- | --- |--- | ---
RCDEVICE_PROTOCOL_COMMAND_5KEY_CONNECTION | 0x04 | Send handshake events and disconnected events to the camera | RCDEVICE_PROTOCOL_FEATURE_SIMULATE_5_KEY_OSD_CABLE

###### Request packet structure, the length is fixed to 4 bytes：
Header | Command ID | Action ID | crc8
--- | --- | --- | ---
0xCC | 0x04 | Refer to the Action section for specific values | Check code

###### Action
Action | Value | Description
--- | --- | --- 
RCDEVICE_PROTOCOL_5KEY_FUNCTION_OPEN   | 0x01 | Initiate a handshake action to the camera
RCDEVICE_PROTOCOL_5KEY_FUNCTION_CLOSE  | 0x02 | Initiate a disconnection action to the camera

###### Response packet structure, the length is fixed to 3 bytes：
Header| Action ID + Response result combination | crc8
--- | --- | ---
0xCC| [ (Action ID << 4) + Response result(1：Succes 0：Failure) ] | Check code

## Device Setting Access
![image](http://o9zlngukm.bkt.clouddn.com/RUNCAM%20DEVICE%20PROTOCOL-DEVICE%20SETTING%20ACCESS.png)

#### Reserved Setting IDs
Setting | ID | Type| Description | Access Mode
--- | --- | --- | --- | ---
SETTINGID_DISP_CHARSET | 0 | TEXT_SELECTION | This setting is store current charset of the device | Read & Write
SETTINGID_DISP_COLUMNS | 1 | UINT8 | Read the number of columns displayed on the screen line | Read only
SETTINGID_DISP_TV_MODE | 2 | TEXT_SELECTION | Read and set the camera's TV mode(NTSC,PAL) | Read & Write
SETTINGID_DISP_SDCARD_CAPACIT | 3 | STRING | Read the camera's memory card capacity | Read only
SETTINGID_DISP_REMAIN_RECORDING_TIME | 4 | STRING | Read the remaining recording time of the camera | Read only
SETTINGID_DISP_RESOLUTION | 5 | TEXT_SELECTION | Read and set the camera's resolution | Read & Write
SETTINGID_DISP_CAMERA_TIME | 6 | STRING | Read and set the camera's time | Read & Write
RESERVED | 7 - 19 | - | these setting are reserved | -

## 6. Get sub settings with special setting ID

Command | ID |Function | Camera feature requirements
--- | --- |--- | ---
RCDEVICE_PROTOCOL_COMMAND_GET_SETTINGS | 0x10 | get a sub settings info with special parent setting id，including setting name, type and current value(in string format) | RCDEVICE_PROTOCOL_FEATURE_DEVICE_SETTINGS_ACCESS

##### Request packet structure, the length is fixed to 5 bytes：
Header | Comman ID | setting ID | Chunk Index | crc8
--- | --- | --- | --- | ---
0xCC | 0x10 | Retrieve the sub settings through the parent setting ID | chunk index | Check code

##### Response packet structure，the length is not fixed:
Field | Value | Size
--- | --- | ---
Remaining Chunk | remaining chunk count | uint8_t
Data Length | The length of data from current field to the CRC field. This length does not include the current field and the CRC field
Setting ID | unique id (Relative to the entire setting tree) | uint8_t
Setting name | setting name | char[], a null-terminated string
Setting value | value of setting | char[], a null-terminated string
Setting ID | unique id (Relative to the entire setting tree) | uint8_t
Setting name | setting name | char[], a null-terminated string
Setting value | value of setting | char[], a null-terminated string
... | ... | ...
... | ... | ...
crc | crc8 code | uint8_t


## 7. Read a setting detail
Command | ID |Function | Camera feature requirements
--- | --- |--- | ---
RCDEVICE_PROTOCOL_COMMAND_READ_SETTING_DETAIL | 0x11 | Retrieve the detail of setting, e.g it's maybe including max value, min value and etc. This command can not be called for the setting type with  Folder and Static | RCDEVICE_PROTOCOL_FEATURE_DEVICE_SETTINGS_ACCESS

##### Request packet structure, the length is fixed to 5 bytes：
Header | Comman ID | Setting ID | Chunk Index | crc8
--- | --- | --- | --- | ---
0xCC | 0x11 | setting ID | Chunk Index | Check code

##### Response packet structure，the length is not fixed:
Field  | Size | Description
--- | --- | ---
Remaining Chunk | remaining chunk count | uint8_t
Data length |  uint8_t | The length of data from current field to the CRC field. This length does not include the current field and the CRC field
setting type | uint8_t | the type of setting，refer to 'setting type' section to know more
value | current value, the size is depending on setting | the current value of setting
min value | the size is depending on setting | max value
max value | the size is depending on setting | min value
decimal point | uint16_t | the digtal count after decimal point
step size | the size is depending on setting | the increment/decrement value when modifying the setting
max string size | uint8_t | max size of string
text_selections | char[] | a null-terminated string，the content is all available string in the setting, they are separated by a semicolon(;)
crc | uint8_t | crc8 code

#### setting type
| available setting type | setting id
| --- | ---
| UINT8 | 0
| INT8 | 1
| UINT16 | 2
| INT16 | 3
| FLOAT | 8
| TEXT_SELECTION | 9
| STRING | 10
| FOLDER | 11
| INFO | 12

INTEGER  
when setting type is UINT8, INT8, UINT16 or INT16，the min value, max value, step size will be returned from Device，and the size of min value, max value and step size are depending on their setting type, e.g if the setting type is UINT8, then min value and max value are uint8_t.

FLOAT  
min value, max value, decimal point, step size will be returned, the type of step size is int32_t

TEXT_SELECTION  
text_selections will be returned as a null-terminated string, the content is all available string in the setting, they are separated by a semicolon(;)

STRING  
max string size will be returned, it's used to limit the max size of the string when user editing it.

FOLDER  
If the setting type is FOLDER, means it contains a set of settings. This  setting can't be modified, when you call Get Detail Command(0x7) with it, it will return a empty response and the error code won't be zero.

INFO  
if the settings type is INFO，this field is same with FOLDER, can't be modified.

COMMAND  
not design yet


## 8. Write a setting
Command | ID |Function | Camera feature requirements
--- | --- |--- | ---
RCDEVICE_PROTOCOL_COMMAND_WRITE_SETTING | 0x13 | change the value of special setting，can't call this command with the setting type of FOLDER and INFO | RCDEVICE_PROTOCOL_FEATURE_DEVICE_SETTINGS_ACCESS

##### Request packet structure, the length is not fixed：
Header | Command ID | Setting ID | value | crc8
--- | --- | --- | --- | --- | ---
0xCC | 0x13 | setting ID | value of the setting, size is depending on setting type | Check code

INTEGER  
when setting type is UINT8, INT8, UINT16 or INT16，the value type is integer, the difference is the size, e.g if the setting type is UINT8, the vlaue field size is uint8_t, same with others.

FLOAT  
a null-terminated string, it describing a float value

TEXT_SELECTION  
the index in text_selections that point to new value.

STRING  
a null-terminated string

COMMAND  
not design yet


##### Response packet structure，the length is fixed to 4 bytes:
Field  | Size | Description
--- | --- | ---
result code | |uint8_t | if value is 0, it means write opertaion succeed 
update menu items | uint8_t | if the value of this field is not zero, the FC size should resend the RCDEVICE_PROTOCOL_COMMAND_GET_SETTINGS(0x10) to retrieve the settings of current page.
crc | uint8_t | crc code

## 9. Fill screen  area
Command | ID |Function | Camera feature requirements
--- | --- |--- | ---
RCDEVICE_PROTOCOL_COMMAND_DISP_FILL_REGION | 0x20 | Fill a area with a special char

##### Request packet structure, the length is not fixed：
Header | Comman ID | x | y | width | height | character | crc8
--- | --- | --- | --- | --- | --- | --- | ---
0xCC | 0x20 | x | y | width | height | the character that going to fill the  area| Check code

## 10. write a single character
Command | ID |Function | Camera feature requirements
--- | --- |--- | ---
RCDEVICE_PROTOCOL_COMMAND_DISP_WRITE_CHAR | 0x21 | Write a character at special position

##### Request packet structure, the length is not fixed：
Header | Comman ID | x | y | character | crc8
--- | --- | --- | --- | --- | ---
0xCC | 0x21 | x | y | the character that going to draw | Check code

## 11. Write a string horizontally
Command | ID |Function | Camera feature requirements
--- | --- |--- | ---
RCDEVICE_PROTOCOL_COMMAND_DISP_WRITE_HORT_STRING | 0x22 | Write a character at special horizontal position

##### Request packet structure, the length is not fixed：
Header | Comman ID | string length | x | y | string | crc8
--- | --- | --- | --- | --- | --- | --- 
0xCC | 0x22 | the length of string(60 is max length) | x | y |the string that going to draw | Check code

## 12. Write a string vertical
Command | ID |Function | Camera feature requirements
--- | --- |--- | ---
RCDEVICE_PROTOCOL_COMMAND_DISP_WRITE_VERT_STRING | 0x23 | Write a character at special vertical position

##### Request packet structure, the length is not fixed：
Header | Comman ID | string length | x | y | string | crc8
--- | --- | --- | --- | --- | --- | --- 
0xCC | 0x23 | the length of string(60 is max length) | x | y |the string that going to draw | Check code

## 13. Write a chars
Command | ID |Function | Camera feature requirements
--- | --- |--- | ---
RCDEVICE_PROTOCOL_COMMAND_DISP_WRITE_CHARS | 0x24 | Write a character at special position

##### Request packet structure, the length is not fixed：
Header | Comman ID| data length | data | crc8
--- | --- | --- | --- | --- 
0xCC | 0x24 | the length of data(60 is max length) | The data is used to draw different characters at one or more locations, each of which needs to occupy 3 bytes, which is x, y, char. Allows up to 20 sets of data, that means the maximum length can not exceed 60 bytes. | Check code