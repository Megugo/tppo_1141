import asyncio
import json
import ast

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

reley_condition = {1:0,
                   2:0,
                   3:0,
                   4:0,
                   5:0,
                   6:0}

prev_condition = {}

writers_for_broadcast = []

json_out = {"data":""}

def get_reley_status():
    with open("f.txt", "r") as f:
        try:
            conditions = f.readline().strip("\n").split(" ")[:6]
            for i in reley_condition:
                reley_condition[i] = int(conditions[i-1])

            status_broadcast()
            print(f"Current reley conditions:\n{json.dumps(reley_condition, indent=2)}")
        except IndexError:
            print("Error: Not enough values from reley file")
            exit(0)

class MyEventHandler(FileSystemEventHandler):
    def on_closed(self, event):
        if event.src_path == './f.txt':
            get_reley_status()

def status_broadcast() -> None:
    json_out["data"] = json.dumps(reley_condition)

    for wrt in writers_for_broadcast:
        send_json(wrt,json_out)

def send_json(writer,json_dict):
    try:
        writer.write(json.dumps(json_dict).encode())
    except ConnectionError as e:
        print(f"Can't send to {writer.get_extra_info('peername')[0]}.\n Error: ", e)

async def handler(reader: asyncio.StreamReader,writer: asyncio.StreamWriter)->None:
    out_data = None
    addr,port = writer.get_extra_info("peername")
    print(f"Connected: Addr:{addr}, port:{port}\n")
    broadcasting = False


    while True:
        raw_data = await reader.read(1000)
        try:
            data = json.loads(raw_data)
        except json.decoder.JSONDecodeError as e:
            send_json(writer,{"data":f"Error: {e}"})
            print("Error: ", e)
            continue

        print(f"Received data from {addr}: {data}\n")

        command = data["command"]

        if "1" in command and len(data)>1:
            msg = data["data"]
            prev_condition = reley_condition.copy()
            try:
                dict_msg = ast.literal_eval(msg)
                if type(dict_msg) is dict:
                    for i in dict_msg:
                        if (dict_msg[i] in [0,1]) and i in reley_condition.keys() :
                            reley_condition[i]= dict_msg[i]

                    if prev_condition!=reley_condition:
                        json_out["data"] = "Conditions changed"
                        send_json(writer,json_out)
                        with open("f.txt", "w") as f:
                            str_conditions =" ".join(str(reley_condition[c]) for c in reley_condition)
                            f.write(str_conditions)

                    else:
                        json_out["data"] = "Nothing changed"
                        send_json(writer,json_out)

                else:
                    json_out["data"] = "Not a dict"
                    send_json(writer,json_out)

            except LookupError:
                json_out["data"] = "wrong dict"
                send_json(writer,json_out)
            except SyntaxError:
                json_out["data"] = "wrong dict"
                send_json(writer,json_out)
            except ValueError:
                json_out["data"] = "wrong dict"
                send_json(writer,json_out)

        elif "2" == command and len(data)>1:
            msg = set(data["data"].split(","))
            channels =[]
            for i in msg:
                if int(i) not in channels and 0<int(i)<7:
                    channels.append(int(i))
            channels.sort()
            selected_channels = {}
            for i in channels:
                try:
                    selected_channels[i] = reley_condition[i]
                except KeyError:
                    pass
            json_out["data"] = selected_channels
            send_json(writer,json_out)

        elif "3" == command:
            if broadcasting == True:
                broadcasting = False
                writers_for_broadcast.remove(writer)
                json_out["data"] = "Broadcasting stoped"
                send_json(writer,json_out)
                print(f"{addr} removed from broadcast\n")

            elif broadcasting == False:
                broadcasting = True
                writers_for_broadcast.append(writer)
                json_out["data"] = "Broadcasting started"
                send_json(writer,json_out)
                print(f"{addr} added to broadcast\n")

        else:
            json_out["data"] = "Wrong command or not enough values"
            send_json(writer,json_out)

        await writer.drain()

        if data["command"] == "exit" or not data["command"]:
            print(f"{addr} disconnected")
            if broadcasting == True:
                writers_for_broadcast.remove(writer)
                print(f"{addr} removed from broadcast\n")
            break

    writer.close()

async def run_server() -> None:
    server = await asyncio.start_server(handler, "127.0.0.1", 8888)
    async with server:
        await server.serve_forever()

if __name__ == "__main__":

    get_reley_status()

    observer = Observer()
    observer.schedule(MyEventHandler(), ".")
    observer.start()

    asyncio.run(run_server())

    observer.stop()
    observer.join()
