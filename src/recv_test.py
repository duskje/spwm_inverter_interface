from serial import Serial

while True:
    with Serial('COM5', 9600, timeout=1) as s:
        msg_len = s.read()

        if msg_len:
            data = s.read(int(msg_len[0]))

            print(data)

