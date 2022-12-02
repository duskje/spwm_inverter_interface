from serial import Serial

from main import MsgType, CouldNotConnectToDeviceError

with Serial('COM4', 9600, timeout=10, write_timeout=0) as s:
    msg_len = s.read()

    if msg_len:
        data = s.read(int(msg_len[0]))

        if data[0] != MsgType.FETCH:
            print(MsgType.CONN == data[0])

            raise CouldNotConnectToDeviceError('FETCH no recibido.')
    else:
        raise CouldNotConnectToDeviceError('FETCH timeout.')

    PR2 = 49
    CCPRxL = 4
    CCPxCON = 2

    msg_len = 4

    s.write(bytearray([msg_len, MsgType.SYNC, PR2, CCPRxL, CCPxCON]))

    msg_len = s.read(1)

    if msg_len:
        data = s.read(int(msg_len[0]))
        print(data)

        if data[0] != MsgType.ACK:
            raise CouldNotConnectToDeviceError('ACK no recibido.')
    else:
        raise CouldNotConnectToDeviceError('ACK timeout.')

    print('ok')