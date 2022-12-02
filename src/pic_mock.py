from serial import Serial
from main import MsgType, CouldNotConnectToDeviceError
from types import SimpleNamespace


def conn(s: Serial):
    msg_len = 1

    s.write(bytearray([msg_len, MsgType.CONN]))

    msg_len = s.read()

    if msg_len:
        data = s.read(int(msg_len[0]))

        if data[0] != MsgType.ACK:
            raise CouldNotConnectToDeviceError('ACK no recibido')
    else:
        raise CouldNotConnectToDeviceError('ACK timeout')

    PR2 = 49
    CCPRxL = 4
    CCPxCON = 2

    s.write(bytearray([4, MsgType.SYNC, PR2, CCPRxL, CCPxCON]))

    msg_len = s.read()

    if msg_len:
        data = s.read(int(msg_len[0]))

        if data[0] != MsgType.ACK:
            raise CouldNotConnectToDeviceError('ACK no receibido')
    else:
        raise CouldNotConnectToDeviceError('ACK timeout')


def recv(s: Serial, status: SimpleNamespace):
    msg_len = 1

    s.write(bytearray([msg_len, MsgType.FETCH]))

    msg_len = s.read()

    if msg_len:
        data = s.read(int(msg_len[0]))

        if data[0] == MsgType.EXIT:
            print('desconecatdo')

            status.connected = False
            return
        else:
            print('PR2: {}, CCPRxL: {}, CCPxCON: {}'.format(*(int(byte) for byte in data[1:])))
    else:
        status.retry -= 1

        raise CouldNotConnectToDeviceError("FETCH timeout")

    msg_len = 1

    s.write(bytearray([msg_len, MsgType.ACK]))

    status.retry = 3


with Serial('COM5', 9600, timeout=0.5, write_timeout=0) as s:
    MAX_RETRIES = 3

    status = SimpleNamespace(connected=False, retry=MAX_RETRIES)

    while True:
        status.retry = MAX_RETRIES

        if not status.connected:
            try:
                print('Intentando conectarse...')

                conn(s)
            except CouldNotConnectToDeviceError:
                continue

            status.connected = True
        else:
            if status.retry:
                try:
                    print('Conectado.')

                    recv(s, status)
                except CouldNotConnectToDeviceError:
                    if status.retry == 0:
                        status.connected = False
