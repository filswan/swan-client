## If you are a client who wants to send deals


Client Tool provides the following functions:
* Encrypt and decrypt file with AES.
* Generate Car files from downloaded source files with or without Lotus.
* Generate metadata e.g. Car file URI, start epoch, etc. and save them to a metadata CSV file.
* Propose deals based on the metadata CSV file.
* Generate a final CSV file contains deal CIDs and miner id for miner to import deals.
* Create tasks on Swan Platform.
* Send deal automatically to auto-bid miners.


## Basic Concept

### Task

In swan project, a task can contain multiple offline deals. There are two basic type of tasks:

- Public Task
    * A public task is a deal set for open bid. If the bid mode is set to manuall,after bidder win the bid, the task holder needs to propose the task to the winner. If the bid mode is set to auto-bid, the task will be automatically assigned to a selected miner based on reputation system and Market Matcher.
- Private Task. 
    * A private task is used to propose deals to a specified miner.

### Offline Deal

The size of an offline deal can be up to 64 GB. It is suggested to create a CSV file contains the following information: 
uuid|miner_id|deal_cid|file_source_url|md5|start_epoch
------------|-------------|-------------|-------------|-------------|-------------
0b89e0cf-f3ec-41a3-8f1e-52b098f0c503|f047419|bafyreid7tw7mcwlj465dqudwanml3mueyzizezct6cm5a7g2djfxjfgxwm|http://download.com/downloads/fil.tar.car| |544835

This CSV file is helpful to enhance the data consistency and rebuild the graph in the future. 
uuid is generated for future index purpose.


## Prerequisite

- Lotus node
- go 1.15+  
- python 3.7+
- pip3


## Config

In config.toml

```
[main]
api_key = ""
access_token = ""
api_url = "https://api.filswan.com"
storage_server_type = "ipfs server"

[web-server]
host = "https://nbai.io"
port = 443
path = "/download"

[ipfs-server]
gateway_address = "/ip4/127.0.0.1/tcp/8080"

[sender]
bid_mode = 1
offline_mode = false
output_dir = "/tmp/tasks"
public_deal = true
verified_deal = true
fast_retrieval = true
skip_confirmation = false
generate_md5 = false
wallet = ""
max_price = "0"
start_epoch_hours = 96
expire_days = 4
```

#### main

Main section defines the token used for connecting with Swan platform. This part can be ignored if offline_mode is set to
true in [sender] section

- **api_key & access_token:** Acquire from [Filswan](https://www.filswan.com) -> "My Profile"->"Developer Settings". You
  can also check the [Guide](https://nebulaai.medium.com/how-to-use-api-key-in-swan-a2ebdb005aa4)
- **api_url:** Default: "https://api.filswan.com"

#### web-server

web-server is used to upload generated Car files. Miner will download Car files from this web-server.
The downloadable URL in the CSV file is built with the following format: host+port+path+filename,
e.g. http://nbai.io:8080/download/<filename>

#### ipfs-server

ipfs-server is used to upload generated Car files. Miner will download Car files from this ipfs-server.
The downloadable URL in the CSV file is built with the following format: host+port+ipfs+hash,
e.g. http://host:port/ipfs/QmPrQPfGCAHwYXDZDdmLXieoxZP5JtwQuZMUEGuspKFZKQ

#### sender

- **bid_mode:** [0/1] Default 1. If it is set to 1, autobid mode is on which means public tasks posted will receive automatically bids from miners and tasks will be sent automatically after auto bids. In contrast, 0 represents the manual mode as public tasks need to be bid manually by miners and sent manually.
- **offline_mode:** [true/false] Default false. If it is set to true, you will not be able to create Swan task on filswan.com, but you can still create CSVs and Car Files for sending deals
- **output_dir:** Output directory for saving generated Car files and CSVs

- **public_deal:** [true/false] Whether deals in the tasks are public deals
- **verified_deal:** [true/false] Whether deals in this task are going to be sent as verified
- **fast_retrieval:** [true/false] Indicates that data should be available for fast retrieval
- **generate_md5:** [true/false] Whether to generate md5 for each car file, note: this is a resource consuming action
- **skip_confirmation:** [true/false] Whether to skip manual confirmation of each deal before sending
- **wallet:**  Wallet used for sending offline deals
- **max_price:** Max price willing to pay per GiB/epoch for offline deal
- **start_epoch_hours:** start_epoch for deals in hours from current time
- **expired_days:** expected completion days for miner sealing data 

### Installation:
#### Ubuntu/Debian

Install and create virtualenv

```shell
sudo apt-get update
sudo apt-get upgrade -y

# Install Git
sudo apt install git -y

# Checkout the source and install
git clone https://github.com/filswan/swan-client.git

cd swan-client/

sh install.sh

. ./activate 
```

## How to use

### Step 0. Encrypt and decrypt file with AES (Optional)

#### Step 0.1 Password keyfile generation   
   
For safety reasons, files need to be encrypted before generating Car files. 

First of all, generate a file which contains the password you pick.

```shell
python3 swan_cli.py keygen --password [password] --key_filename [key_filename] 
```

For example,

```shell
python3 swan_cli.py keygen --password MySwanClientPassword --key_filename MyPassword 
```

The output key file with AES namely:

```shell
MyPassword.key
```

#### Step 0.2 File encryption   
   
For encryption:

```shell
python3 swan_cli.py encrypt --input-file [input_file] --out-encrypted-file [out_encrypted_file] --key_file [keyfile]
```
For example,

```shell
python3 swan_cli.py encrypt --input-file ../source/sample.zip --out-encrypted-file ../encryption/sample.enc --key_file MyPassword.key
```

#### Step 0.3 File decryption     
   
For decryption:

```shell
python3 swan_cli.py decrypt --input-encrypted-file [input_encrypted_file] --out-decrypted-file [out_decrypted_file] --key_file [keyfile]
```
   
For example,

```shell
python3 swan_cli.py decrypt --input-encrypted-file ../encryption/sample.enc --out-decrypted-file ../decryption/sample.zip --key_file MyPassword.key
```

Credits should be given to jokkebk for the encryption and decryption process. More information can be found in https://github.com/jokkebk/fileson

### Step 1. Generate Car files for offline deal

For both public task and private task, you need to generate Car files

#### Step 1.1 Generate Car files using Lotus (option 1)
```shell
python3 swan_cli.py car --input-dir [input_files_dir] --out-dir [car_files_output_dir] 
```

Note: The input dir and out dir shall only be in format of Absolute Path.   
   
The output will be like:

```shell
INFO:root:Generating car file from: [input_file_dir]/ubuntu-15.04-server-i386.iso.tar
INFO:root:car file Generated: [car_files_output_dir]/ubuntu-15.04-server-i386.iso.tar.car, piece cid: baga6ea4seaqbpggkuxz7gpkm2wf3734gkyna3vb4p7bm3qcbl4gb4jgh22vj2pi, piece size: 15.88 GiB
INFO:root:Generating data CID....
INFO:root:Data CID: bafykbzacebbq4g73e4he32ahyynnamrft2tva2jyjt5fsxfqv76anptmyoajw
INFO:root:Car files output dir: [car_files_output_dir]
INFO:root:Please upload car files to web server or ipfs server.
```
If --out-dir is not provided, then the output directory for the car files will be: output_dir (specified in the configuration file) + a random uuid

For example: /tmp/tasks/7f33a9d6-47d0-4635-b152-5e380733bf09

#### Step 1.2 Generate Car files without using Lotus (option 2)

To use the generation locally, make sure go is available before starting.

Generate car files using golang

```shell
python3 swan_cli.py gocar --input-dir [input_files_dir] --out-dir [car_files_output_dir] 
```

For example,

```shell
python3 swan_cli.py gocar --input-dir ../encryption --out-dir ../gocar
```   

Meanwhile, a car.csv and a manifest.csv with the detail information of the corresponding car files will be generated in the same output directory.    
   
Credits should be given to filedrive-team. More information can be found in https://github.com/filedrive-team/go-graphsplit.

### Step 2: Upload Car files to webserver or ipfs server

After the car files are generated, you need to copy the files to a web-server manually, or you can upload the files to local ipfs server.

If you decide to upload the files to local ipfs server:
```shell
python3 swan_cli.py upload --input-dir [input_file_dir]
```
The output will be like:
```shell
INFO:root:Uploading car file [car_file]
INFO:root:Car file [car_file] uploaded: http://127.0.0.1:8080/ipfs/QmPrQPfGCAHwYXDZDdmLXieoxZP5JtwQuZMUEGuspKFZKQ
```

### Step 3. Create a task

#### Options 1: Private Task

in config.toml: set public_deal = false

```shell
python3 swan_cli.py task --input-dir [car_files_dir] --out-dir [output_files_dir] --miner [miner_id] --dataset [curated_dataset] --description [description]
```
**--input-dir (Required)** Input directory where the generated car files and car.csv are located

**--out-dir (optional)** Metadata CSV and Swan task CSV will be generated to the given directory. Default: output_dir specified in config.toml

**--miner (Required)** Miner Id you want to send private deal to

**--dataset (optional)** The curated dataset from which the Car files are generated

**--description (optional)** Details to better describe the data and confine the task or anything the miner needs to be informed.

The output will be like:
```shell
INFO:root:Swan Client Settings: Public Task: False  Verified Deals: True  Connected to Swan: True CSV/car File output dir: /tmp/tasks/[output_files_dir]
INFO:root:['lotus', 'client', 'deal', '--from', 't3u4othyfcqjiiveolvdczcww3rypxgonz7mnqfvbtf2paklpru5f6csoajdfz5nznqy2kpr4eielsmksyurnq', '--start-epoch', '547212', '--manual-piece-cid', 'baga6ea4seaqcqjelghbfwy2r6fxsffzfv6gs2gyvc75crxxltiscpajfzk6csii', '--manual-piece-size', '66584576', 'bafykbzaceb6dtpjjisy5pzwksrxwfothlmfjtmcjj7itsvw2flpp5co5ikxam', 't01101', '0.000000000000000000', '1051200']
INFO:root:wallet: t3u4othyfcqjiiveolvdczcww3rypxgonz7mnqfvbtf2paklpru5f6csoajdfz5nznqy2kpr4eielsmksyurnq
INFO:root:miner: t01101
INFO:root:price: 0
INFO:root:total cost: 0.000000000000000000
INFO:root:start epoch: 547212
Press Enter to continue...
INFO:root:Deal sent, deal cid: bafyreibnmon4sby7ibwiezcjgjge7mshl3h24vftzkab5fqm4ll2voarna, start epoch: 547212
INFO:root:Swan deal final CSV Generated: /tmp/tasks/[output_files_dir]/swan-client-demo-deals.csv
INFO:root:Refreshing token
INFO:root:Working in Online Mode. A swan task will be created on the filwan.com after process done. 
INFO:root:Metadata CSV Generated: /tmp/tasks/[output_files_dir]/swan-client-demo-metadata.csv
INFO:root:Swan task CSV Generated: /tmp/tasks/[output_files_dir]/swan-client-demo.csv
INFO:root:Creating new Swan task: swan-client-demo
INFO:root:New Swan task Generated.
```

#### Options 2: Public Task

in config.toml: set public_deal = true

1. Generate the public task

```shell
python3 swan_cli.py task --input-dir [car_files_dir] --out-dir [output_files_dir] --name [task_name] --dataset [curated_dataset] --description [description]
```

**--input-dir (Required)** Each file under this directory will be converted to a Car file, the generated car file will be located
under the output folder defined in config.toml

**--out-dir (optional)** Metadata CSV and Swan task CSV will be generated to the given directory. Default: output_dir specified in config.toml 

**--name (optional)** Given task name while creating task on Swan platform. Default:
swan-task-uuid

**--dataset (optional)** The curated dataset from which the Car files are generated

**--description (optional)** Details to better describe the data and confine the task or anything the miner needs to be informed

Two CSV files are generated after successfully running the command: task-name.csv, task-name-metadata.csv.

[task-name.csv] is a CSV generated for posting a task on Swan platform or transferring to miners directly for offline import

```
uuid,miner_id,deal_cid,file_source_url,md5,start_epoch,piece_cid
```

[task-name-metadata.csv] contains more content for creating proposal in the next step

```
uuid,source_file_name,source_file_path,source_file_md5,source_file_url,source_file_size,car_file_name,car_file_path,car_file_md5,car_file_url,car_file_size,deal_cid,data_cid,piece_cid,miner_id,start_epoch
```

2. Propose offline deal after miner win the bid. Client needs to use the metadata CSV generated in the previous step
   for sending the offline deals to the miner.

```
python3 swan_cli.py deal --csv [metadata_csv_dir/task-name-metadata.csv] --out-dir [output_files_dir] --miner [miner_id]
```

**--csv (Required):** File path to the metadata CSV file. Mandatory metadata CSV fields: source_file_size, car_file_url, data_cid,
piece_cid

**--out-dir (optional):** Swan deal final CSV will be generated to the given directory. Default: output_dir specified in config.toml

**--miner (Required):** Target miner id, e.g f01276

A csv with name [task-name]-metadata-deals.csv is generated under the output directory, it contains the deal cid and
miner id for miner to process on Swan platform. You could re-upload this file to Swan platform while assign bid to miner or do a
private deal.

The output will be like:

```shell
INFO:root:['lotus', 'client', 'deal', '--from', 'f3ufzpudvsjqyiholpxiqoomsd2svy26jvy4z4pzodikgovkhkp6ioxf5p4jbpnf7tgyg67dny4j75e7og7zeq', '--start-epoch', '544243', '--manual-piece-cid', 'baga6ea4seaqcqjelghbfwy2r6fxsffzfv6gs2gyvc75crxxltiscpajfzk6csii', '--manual-piece-size', '66584576', 'bafykbzaceb6dtpjjisy5pzwksrxwfothlmfjtmcjj7itsvw2flpp5co5ikxam', 'f019104', '0.000000000000000000', '1051200']
INFO:root:wallet: f3ufzpudvsjqyiholpxiqoomsd2svy26jvy4z4pzodikgovkhkp6ioxf5p4jbpnf7tgyg67dny4j75e7og7zeq
INFO:root:miner: f019104
INFO:root:price: 0
INFO:root:total cost: 0.000000000000000000
INFO:root:start epoch: 544243
Press Enter to continue...
INFO:root:Deal sent, deal cid: bafyreicqgsxql7oqkzr7mtwyrhnoedgmzpd5br3er7pa6ooc54ja6jmnkq, start epoch: 544243
INFO:root:Swan deal final CSV /tmp/tasks/[output_files_dir]/task-name-metadata-deals.csv
INFO:root:Refreshing token
eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE2MTQzNzA5ODcsImlhdCI6MTYxNDI4NDU4Nywic3ViIjoiV2pIVkJDYWIxM2FyUURlUldwbkw0QSJ9.Hn8f0z2Ew6DuL2E2ELgpi9_Gj8xrg28S3v31dTUW32s
INFO:root:Updating Swan task.
INFO:root:Swan task updated.
```

### Step 4. Auto send auto-bid mode tasks with deals to auto-bid mode miner
The autobid system between swan-client and swan-provider allows you to automatically send deals to a miner selected by Swan platform. All miners with auto-bid mode on have the chance to be selected but only one will be chosen based on Swan reputation system and Market Matcher.
```
python3 swan_cli_auto.py auto --out-dir [output_file_dir] 
```
**--out-dir (optional):** A new metadata csv and a Swan task CSV will be generated to the given directory. Default: output_dir specified in config.toml
