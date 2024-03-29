from enum import Enum

from serial import Serial, STOPBITS_ONE, EIGHTBITS, PARITY_NONE

from serial_communication import MsgType, CouldNotConnectToDeviceError

from time import sleep


class ModulationIndex(Enum):
    MODULATION_INDEX_80 = 0
    MODULATION_INDEX_81 = 1
    MODULATION_INDEX_82 = 2
    MODULATION_INDEX_83 = 3
    MODULATION_INDEX_84 = 4
    MODULATION_INDEX_85 = 5
    MODULATION_INDEX_86 = 6
    MODULATION_INDEX_87 = 7
    MODULATION_INDEX_88 = 8
    MODULATION_INDEX_89 = 9
    MODULATION_INDEX_90 = 10
    MODULATION_INDEX_91 = 11
    MODULATION_INDEX_92 = 12
    MODULATION_INDEX_93 = 13
    MODULATION_INDEX_94 = 14
    MODULATION_INDEX_95 = 15


def send_conn_message(s: Serial):
    msg_len = 1
    s.write(bytearray([msg_len, MsgType.CONN]))


def recv_syn_message(s: Serial) -> ModulationIndex:
    msg_len = s.read()

    if msg_len:
        data = s.read(int(msg_len[0]))

        if data[0] != MsgType.SYNC:
            raise CouldNotConnectToDeviceError('SYNC no recibido.')

        return ModulationIndex(data[1])
    else:
        raise CouldNotConnectToDeviceError('SYNC timeout.')


def send_ack_message(s: Serial):
    msg_len = 1
    s.write(bytearray([msg_len, MsgType.ACK]))


def send_sync_message(s: Serial, modulation_index: ModulationIndex):
    msg_len = 2
    s.write(bytearray([msg_len, MsgType.SYNC, modulation_index.value]))

def recv_ack_message(s: Serial):
    msg_len = s.read()

    if msg_len:
        data = s.read(int(msg_len[0]))

        if data[0] != MsgType.ACK:
            raise CouldNotConnectToDeviceError('ACK no recibido.')
    else:
        raise CouldNotConnectToDeviceError('ACK timeout.')


def main():
    with Serial('COM10', 9600, timeout=1) as s:
        send_conn_message(s)

        print(recv_syn_message(s))

        send_ack_message(s)

        while True:
            sleep(0.5)

            send_sync_message(s, ModulationIndex.MODULATION_INDEX_80)
            recv_ack_message(s)

            print('SYN enviado.')

