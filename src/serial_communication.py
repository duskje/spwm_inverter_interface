from dataclasses import dataclass
from enum import IntEnum, Enum, auto
from queue import Queue
from threading import Thread
from typing import Optional, Tuple, Any

from serial import Serial, SerialException
from serial.tools.list_ports_common import ListPortInfo

from spwm_indices import ModulationIndex

class MsgType(IntEnum):
    CONN = 1
    ACK = 2
    NACK = 3
    SYNC = 4
    ALIVE = 5
    FETCH = 6
    READY = 7
    EXIT = 8


class CouldNotConnectToDeviceError(Exception):
    pass


@dataclass(frozen=True)
class SerialMessage:
    function: str
    args: Optional[Tuple[Any, ...]]


@dataclass(frozen=True)
class SerialResult:
    value: Any

    @property
    def is_error(self):
        return isinstance(self.value, Exception)


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



def conn(port_name: str, baudrate: int, timeout: float):
    serial_port = Serial(
        port_name,
        baudrate,
        timeout=timeout,
        write_timeout=0
    )

    with serial_port as s:
        send_conn_message(s)

        modulation_index = recv_syn_message(s)

        send_ack_message(s)

        return modulation_index



def sync(s: Serial, modulation_index: ModulationIndex):
    send_sync_message(s, modulation_index)

    recv_ack_message(s)


def serial_communication(
        message_queue: Queue,
        result_queue: Queue,

        baudrate: int = 9600,
        timeout: float = 0.5,
):
    connected_port: Optional[ListPortInfo] = None

    while True:
        value = message_queue.get()

        try:
            if value.function == 'conn':
                port = value.args[0]
                try:
                    result = conn(port, baudrate, timeout)

                    connected_port = port

                    result_queue.put(SerialResult(result))
                except CouldNotConnectToDeviceError:
                    result_queue.put(SerialResult(CouldNotConnectToDeviceError))

            elif value.function == 'sync':
                if connected_port is None:
                    continue

                serial_port = Serial(
                    connected_port,
                    baudrate,
                    timeout=timeout,
                    write_timeout=0
                )

                retries = 5

                modulation_index = value.args[0]

                with serial_port as s:
                    while retries:
                        try:
                            sync(s, modulation_index)

                            break
                        except CouldNotConnectToDeviceError:
                            retries -= 1

                if retries:
                    continue
                else:
                    connected_port = None

                    result_queue.put(SerialResult(CouldNotConnectToDeviceError))

            elif value.function == 'exit':
                if connected_port is None:
                    continue

                serial_port = Serial(
                    connected_port,
                    baudrate,
                    timeout=timeout,
                    write_timeout=0
                )

                with serial_port as s:
                    msg_len = 1

                    s.write(bytearray([msg_len, MsgType.EXIT]))

                connected_port = None
        except SerialException:
            result_queue.put(SerialResult(CouldNotConnectToDeviceError))


class SerialPortStatus(Enum):
    CONNECTED = auto()
    CONNECTING = auto()
    CONN_SYNC = auto()
    NOT_CONNECTED = auto()
    DISCONNECTED = auto()

    TIMEOUT_ERROR = auto()
    COULD_NOT_CONNECT_ERROR = auto()


class SerialPort:
    def __init__(self, baudrate: int = 9600, timeout: float = 0.5):
        # Se crean dos colas para comunic

        self.message_queue = Queue(maxsize=1)
        self.result_queue = Queue(maxsize=1)

        # Abre un proceso

        self.thread = Thread(target=serial_communication,
                             args=(self.message_queue,
                                   self.result_queue,
                                   baudrate,
                                   timeout),
                             daemon=True)

        self.thread.start()

        self.is_connected = False

        self.port_name: Optional[str] = None
        self.status = SerialPortStatus.NOT_CONNECTED

    def connect(self, port_info: ListPortInfo) -> Optional[Tuple[int, int, int]]:
        # Si por alguna razón el usuario, intenta conectarse al

        if port_info.name == self.port_name:
            return

        port_name = port_info.name

        self.message_queue.put(SerialMessage('conn', (port_name,)))

        result: SerialResult = self.result_queue.get()

        if result.value is CouldNotConnectToDeviceError:
            self.port_name = None
            self.is_connected = False

            self.status = SerialPortStatus.COULD_NOT_CONNECT_ERROR

            return None
        else:
            self.port_name = port_name
            self.is_connected = True

            self.status = SerialPortStatus.CONNECTED
            modulation_index: ModulationIndex = result.value

            return (modulation_index.value * 5 + 20) / 100

    def sync(self, modulation_index: float):
        modulation_index = ModulationIndex(int(modulation_index * 100 - 20) / 5)

        if not self.result_queue.empty():
            result = self.result_queue.get()

            if result.value is CouldNotConnectToDeviceError:
                self.is_connected = False
                self.port_name = None

                self.status = SerialPortStatus.TIMEOUT_ERROR

        if self.message_queue.empty() and self.is_connected:
            message = SerialMessage('sync', (modulation_index,))

            self.message_queue.put(message)

    def exit(self):
        self.status = SerialPortStatus.DISCONNECTED

        self.is_connected = False
        self.port_name = None

        self.message_queue.put(SerialMessage('exit', None))


