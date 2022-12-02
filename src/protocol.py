from dataclasses import dataclass
from enum import IntEnum, Enum, auto
from queue import Queue
from threading import Thread
from typing import Optional, Tuple, Any

from serial import Serial, SerialException
from serial.tools.list_ports_common import ListPortInfo

from calculos_siseln import getPR2value, getCCPRxL_CCPxCON
from constants import PICValues


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


def send_message(msg_type: MsgType, data: bytearray):
    pass


def receive_message(msg_type: MsgType):
    pass


def conn(port_name: str, baudrate: int, timeout: float):
    serial_port = Serial(
        port_name,
        baudrate,
        timeout=timeout,
        write_timeout=0
    )

    with serial_port as s:
        msg_len = s.read()

        if msg_len:
            data = s.read(int(msg_len[0]))

            if data[0] != MsgType.CONN:
                raise CouldNotConnectToDeviceError('CONN no recibido.')
        else:
            raise CouldNotConnectToDeviceError('CONN timeout.')

        msg_len = 1

        s.write(bytearray([msg_len, MsgType.ACK]))

        msg_len = s.read()

        if msg_len:
            data = s.read(int(msg_len[0]))

            if data[0] != MsgType.SYNC:
                raise CouldNotConnectToDeviceError('SYNC no recibido.')

            print(msg_len[0])
            print(data)

            PR2, CCPRxL, CCPxCON = [int(byte) for byte in data[1:]]
        else:
            raise CouldNotConnectToDeviceError('SYNC timeout.')

        msg_len = 1

        s.write(bytearray([msg_len, MsgType.ACK]))

        print('pr2, ccprxl, ccpxcon', PR2, CCPRxL, CCPxCON)

        return PR2, CCPRxL, CCPxCON


def sync(s, frequency: float, duty_cycle: float):
    msg_len = s.read()

    if msg_len:
        data = s.read(int(msg_len[0]))

        if data[0] != MsgType.FETCH:
            print('fetch not')
            print(data[0] == MsgType.CONN)
            raise CouldNotConnectToDeviceError('FETCH no recibido.')
    else:
        print('fetch timeout')
        raise CouldNotConnectToDeviceError('FETCH timeout.')

    PR2 = getPR2value(frequency, PICValues.F_OSC, PICValues.TMR2_PRESCALER)
    CCPRxL, CCPxCON = getCCPRxL_CCPxCON(PR2, duty_cycle)

    msg_len = 4

    s.write(bytearray([msg_len, MsgType.SYNC, PR2, CCPRxL, CCPxCON]))

    msg_len = s.read(1)

    if msg_len:
        data = s.read(int(msg_len[0]))

        if data[0] != MsgType.ACK:
            raise CouldNotConnectToDeviceError('ACK no recibido.')
    else:
        raise CouldNotConnectToDeviceError('ACK timeout.')


def serial_communication(
        message_queue: Queue,
        result_queue: Queue,

        baudrate: int = 9600,
        timeout: float = 5,
):
    connected_port: Optional[ListPortInfo] = None

    while True:
        value = message_queue.get()

        try:
            if value.function == 'conn':
                try:
                    result = conn(value.args[0], baudrate, timeout)

                    connected_port = value.args[0]

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

                with serial_port as s:
                    while retries:
                        try:
                            sync(s, value.args[0], value.args[1])
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
                    s.read()

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
    def __init__(self, baudrate: int = 9600, timeout: float = 5):
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

            return result.value

    def sync(self, frequency: float, duty_cycle: float):
        if not self.result_queue.empty():
            result = self.result_queue.get()

            if result.value is CouldNotConnectToDeviceError:
                self.is_connected = False
                self.port_name = None

                self.status = SerialPortStatus.TIMEOUT_ERROR

        if self.message_queue.empty() and self.is_connected:
            message = SerialMessage('sync', (frequency, duty_cycle))

            self.message_queue.put(message)

    def exit(self):
        self.status = SerialPortStatus.DISCONNECTED

        self.is_connected = False
        self.port_name = None

        self.message_queue.put(SerialMessage('exit', None))


