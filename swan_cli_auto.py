import argparse
import os
import time
import logging

from task_sender.swan_task_sender import get_task_info,get_assigned_tasks,send_autobid_deal,update_assigned_task



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Swan client autobid')

    parser.add_argument('function', metavar='task/deal', choices=['auto'], type=str, nargs="?",
                        help='Automatically send autobid deals')

    parser.add_argument('--out-dir', dest='out_dir', help="Path to the dir to metadata csv and task csv")
    parser.add_argument('--config', dest='config_path', default="./config.toml",
                        help="Path to the config file (default: ./config.toml)")

    args = parser.parse_args()

    config_path = args.__getattribute__('config_path')
    config_path = os.path.abspath(config_path)


    if args.__getattribute__('function') == "auto":
        out_dir = args.__getattribute__('out_dir')
        while True:
            try:
                tasks_dict = get_assigned_tasks(config_path)
                for task in tasks_dict["Assigned tasks"]:
                    assigned_task = get_task_info(task["uuid"],config_path)
                    assigned_task_info = assigned_task["task"]
                    if assigned_task_info:
                        assigned_miner_id = assigned_task_info['miner_id']
                        deals = assigned_task['deals']
                        info_output_csv_path = send_autobid_deal(deals,assigned_miner_id,assigned_task_info,config_path,out_dir)
                        if info_output_csv_path:
                            update_assigned_task(config_path, assigned_task_info['uuid'], info_output_csv_path)
                        else:
                            continue
                time.sleep(30)
            except Exception as e:
                logging.error(e)
                time.sleep(30)




