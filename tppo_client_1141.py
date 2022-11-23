import asyncio
import json

def info_message():
    print("Commands:\n 1 - переключает заданные каналы,\n формат записи '1 {chanel_number:condition}', condition = [0,1], chanel_number = [1,2,3,4,5,6]\n")
    print(" 2 - получает состояние заданных каналов,\n формат '2 chanel_number_1,chanel_number_2...'\n")
    print(" 3 - включает режим отслеживания обновлений состояния реле,\n формат '3', CTRL+C отключает режим отслеживания\n")
    print(" info - для получения информации по командам\n")
    print(" exit - выход из приложения\n")

def send_json(writer,json_dict):
    try:
        writer.write(json.dumps(json_dict).encode())
    except ConnectionError as e:
        print("Error: ", e)

async def tcp_echo_client():
    reader, writer = await asyncio.open_connection(
        '127.0.0.1', 8888)
    info_message()

    while True:
        message = input("Input command: ")

        if message == 'info':
            info_message()
            continue

        splited_message = message.split(" ")[:2]

        if splited_message[0] in ["1","2"] and len(splited_message)>1:
            json_message = {"command":splited_message[0],"data":splited_message[1]}

        elif splited_message[0] in ['3',"exit"]:
            json_message = {"command":splited_message[0],"data":""}

        else:
            print("Wrong command or not enough values")
            continue

        if message:
            print(f'\nSend: {json.dumps(json_message, indent=2)}\n')
            send_json(writer,json_message)

        if splited_message[0]== '3':
            while True:
                try:
                    data = await reader.read(1000)
                    if data!=b"":
                        print(f'Received new conditions: {json.loads(data.decode())["data"]}')

                except BaseException:#KeyboardInterrupt:
                    print("Stoping broadcasting")
                    send_json(writer,{"command":"3","data":""})
                    break
        try:
            await writer.drain()
        except ConnectionError as e:
            print("Connection lost")
            exit(0)
        data = await reader.read(1000)

        if message == "exit":
            print("closing")
            break
        if data!=b"":
            try:
                print(f'Received: {json.loads(data.decode())["data"]}\n')
            except json.decoder.JSONDecodeError as e:
                print("Error ", e)

    print('Close the connection')
    try:
        writer.close()
        await writer.wait_closed()
    except BrokenPipeError as e:
        pass

asyncio.run(tcp_echo_client())
