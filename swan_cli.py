import argparse
import os
import random
import string
import csv
import subprocess
import time
import logging
from miner_updater.swan_miner_updater import update_miner_info
from task_sender.deal_sender import send_deals
from task_sender.swan_task_sender import create_new_task, update_task_by_uuid, generate_car_files, go_generate_car_files,upload_car_files


def random_hash(length=6):
    chars = string.ascii_lowercase + string.digits
    ran_hash = ''.join(random.choice(chars) for _ in range(length))
    return ran_hash


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Swan client')

    parser.add_argument('function', metavar='task/deal', choices=['task', 'deal', 'miner', 'car', 'upload','gocar','keygen','encrypt','decrypt','status', 'assign','auto'], type=str, nargs="?",
                        help='Create new Swan task/Send deal/Update miner info/Generate car file/Get task status')

    parser.add_argument('--config', dest='config_path', default="./config.toml",
                        help="Path to the config file (default: ./config.toml)")

    parser.add_argument('--name', dest='task_name', default="swan-task-" + random_hash(),
                        help="Task name (default: hash name)")
    parser.add_argument('--input-dir', dest='input_dir', help="Path to the dir of files ready to create a new task")
    parser.add_argument('--out-dir', dest='out_dir', help="Path to the dir to generate car files and car csv")

    parser.add_argument('--miner', dest='miner_id', help="Miner ID to send deals to.")
    parser.add_argument('--dataset', dest='dataset', help="Curated dataset.")
    parser.add_argument('--description', dest='description', help="Task description.")
    parser.add_argument('--csv', dest='metadata_csv_path', help="The CSV file path of deal metadata.")
    
    parser.add_argument('--password', dest='password', help="The password for encryption and decryption")
    parser.add_argument('--key_filename', dest='key_filename', help="The filename of where encrypted password is restored")
    parser.add_argument('--encrypt', dest='encrypt', help="Encryption: Encrypt input file and output encrypted file")
    parser.add_argument('--decrypt', dest='decrypt', help="Decryption: Decrypt input encrypted file and output decrypted file")
    parser.add_argument('--input-file', dest='input_file', help="Input plainfile")
    parser.add_argument('--out-encrypted-file', dest='out_encrypted_file', help="Output encrypted file")
    parser.add_argument('--input-encrypted-file', dest='input_encrypted_file', help="Input encrypted file")
    parser.add_argument('--out-decrypted-file', dest='out_decrypted_file', help="Output decrypted file")
    parser.add_argument('--key_file', dest='key_file', help="Input file with .key extention where encrypted password is restored for encryption and decryption")

    parser.add_argument('--task', dest='task_uuid', help="Get task status by uuid.")
    parser.add_argument('--bid', dest='bid_id', help="Bid id")

    args = parser.parse_args()

    config_path = args.__getattribute__('config_path')
    config_path = os.path.abspath(config_path)

    if args.__getattribute__('function') == 'keygen':
        password = args.__getattribute__('password')
        if not password:
            print('Please provide --password')
            exit(1)
        key_filename = args.__getattribute__('key_filename')
        command_line = "python3 fileson/fileson_backup.py keygen {} salt > {}.key".format(password, key_filename)
        subprocess.run((command_line), shell=True)
     
    if args.__getattribute__('function') == 'encrypt':
        inputfile= args.__getattribute__('input_file')
        if not inputfile:
            print('Please provide --input-file')
            exit(1)
        outencryptedfile= args.__getattribute__('out_encrypted_file')
        keyfile = args.__getattribute__('key_file')
        command_line = "python3 fileson/fileson_backup.py encrypt {}  {} {}".format(inputfile, outencryptedfile,keyfile)
        subprocess.run((command_line), shell=True)
     
    if args.__getattribute__('function') == 'decrypt':
        inputencryptedfile= args.__getattribute__('input_encrypted_file')
        if not inputencryptedfile:
            print('Please provide --input-encrypted-file')
            exit(1)
        outdecryptedfile= args.__getattribute__('out_decrypted_file')
        keyfile = args.__getattribute__('key_file')
        command_line = "python3 fileson/fileson_backup.py decrypt {}  {} {}".format(inputencryptedfile, outdecryptedfile,keyfile)
        subprocess.run((command_line), shell=True)
          

    if args.__getattribute__('function') == 'car':
        input_dir = args.__getattribute__('input_dir')
        if not input_dir:
            print('Please provide --input-dir')
            exit(1)
        out_dir = args.__getattribute__('out_dir')

        generate_car_files(input_dir, config_path, out_dir)
     
    if args.__getattribute__('function') == 'gocar':
        input_dir = args.__getattribute__('input_dir')
        if not input_dir:
            print('Please provide --input-dir')
            exit(1)
        out_dir = args.__getattribute__('out_dir')

        go_generate_car_files(input_dir, config_path, out_dir)    
     

    if args.__getattribute__('function') == 'upload':
        input_dir = args.__getattribute__('input_dir')
        if not input_dir:
            print('Please provide --input-dir')
            exit(1)

        upload_car_files(input_dir, config_path)

    if args.__getattribute__('function') == 'task':
        input_dir = args.__getattribute__('input_dir')
        if not input_dir:
            print('Please provide --input-dir')
            exit(1)
        input_dir = os.path.abspath(input_dir)
        task_name = args.__getattribute__('task_name')
        miner_id = args.__getattribute__('miner_id')
        out_dir = args.__getattribute__('out_dir')
        curated_dataset = args.__getattribute__('dataset')
        description = args.__getattribute__('description')

        create_new_task(input_dir, out_dir, config_path, task_name, curated_dataset, description, miner_id)

    elif args.__getattribute__('function') == "deal":
        metadata_csv_path = args.__getattribute__('metadata_csv_path')
        if not metadata_csv_path:
            print('Please provide --csv')
            exit(1)
        metadata_csv_path = os.path.abspath(metadata_csv_path)
        miner_id = args.__getattribute__('miner_id')
        if not miner_id:
            print('Please provide --miner')
            exit(1)
        out_dir = args.__getattribute__('out_dir')
        with open(metadata_csv_path, 'r') as csvfile:
            reader = csv.reader(csvfile)
            column = [row[0] for row in reader]
            task_uuid = column[1]
            metadata_deal_csv_path = send_deals(config_path, miner_id, metadata_csv_path=metadata_csv_path, task_uuid=task_uuid, out_dir=out_dir)
            with open(metadata_deal_csv_path, 'r') as deal_csvfile:
                update_task_by_uuid(config_path, task_uuid, miner_id, deal_csvfile)

    elif args.__getattribute__('function') == "miner":
        miner_id = args.__getattribute__('miner_id')
        if not miner_id:
            print('Please provide --miner')
            exit(1)

        update_miner_info(miner_id, config_path)









