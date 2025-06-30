import time
import requests
import json
import logging
import serial
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Конфигурация
SERVER_URL = 'http://localhost:5000'
CLIENT_ID = 'scale001'
POLL_INTERVAL = 10
RECONNECT_INTERVAL = 30

# Настройки весов
SERIAL_PORT = 'COM3'
BAUDRATE = 9600

# Константы команд и длин
COMMANDS = {
    "read_logo2": b'\x97',
    "write_logo2": b'\x8C',
    "write_logo_roste": b'\x93',
    "read_user_settings": b'\x95',
    "write_user_settings": b'\x8A',
    "read_factory_settings": b'\x9B',
    "get_status": b'\x89',
    "get_plu": b'\x81',
    "delete_plu": b'\x8D',
    "create_plu": b'\x82',
    "get_message": b'\x83',
    "create_message": b'\x84',
    "delete_message": b'\x8E',
    "reset_plu_totals": b'\x92',
    "get_total_sales": b'\x85',
    "reset_total_sales": b'\x86',
    "bind_plu_to_key": b'\x8B',
    "get_plu_by_key": b'\x96'
}

LENGTHS = {
    "logo2": 512,
    "logo_roste": 384,
    "user_settings": 9,
    "factory_settings": 13,
    "current_status": 15,
    "plu": 100,
    "message": 400,
    "plu_write": 83,
    "message_write": 402,
    "total_sales": 40,
    "plu_code": 4,
}

ERROR_RESPONSE = b'\xEE'

class ScaleClient:
    def __init__(self, port=SERIAL_PORT, baudrate=BAUDRATE):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self._ready_state = False
        self._last_reconnect_attempt = 0
        self._connection_attempts = 0
        self._max_connection_attempts = 5
        
        self._connect(port, baudrate)

    def _connect(self, port: str, baudrate: int):
        logging.info(f"Попытка подключения к {port} на {baudrate}")
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
            
            self.ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=2,
                write_timeout=3
            )
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            
            self.ser.write(b'\x01')
            if self._wait_ready():
                logging.info(f"Подключение к весам установлено: {self.ser.is_open}")
                self._connection_attempts = 0
                return True
            else:
                logging.error("Не удалось установить связь с весами")
                self.ser.close()
                self.ser = None
                self._ready_state = False
                return False
                
        except Exception as e:
            logging.error(f"Ошибка подключения к весам: {str(e)}")
            self.ser = None
            self._ready_state = False
            return False

    def try_reconnect(self):
        current_time = time.time()
        
        if current_time - self._last_reconnect_attempt < RECONNECT_INTERVAL:
            return False
            
        self._last_reconnect_attempt = current_time
        self._connection_attempts += 1
        
        logging.info(f"Попытка переподключения #{self._connection_attempts}")
        
        if self._connect(self.port, self.baudrate):
            return True
        else:
            if self._connection_attempts >= self._max_connection_attempts:
                logging.warning(f"Достигнуто максимальное количество попыток подключения ({self._max_connection_attempts})")
                if self._connection_attempts >= self._max_connection_attempts * 2:
                    self._connection_attempts = 0
            return False

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            logging.info(f"Порт {self.port} закрыт")
        self._ready_state = False

    def is_ready(self) -> bool:
        return self._ready_state and self.ser and self.ser.is_open

    def _wait_ready(self, timeout=10.0) -> bool:
        if not self.ser:
            return False
            
        start = time.time()
        while time.time() - start < timeout:
            byte = self.ser.read(1)
            logging.info(f"получено от весов {byte.hex()}")
            if not byte:
                continue
            if byte == b'\xEE':
                logging.info("Ошибка выполнения команды (b'\\xEE')")
                ready = self.ser.read(1)
                if ready == b'\x80':
                    self._ready_state = True
                return True
            if byte == b'\x80':
                logging.info("Получен байт готовности от весов")
                self._ready_state = True
                return True
            logging.debug(f"Пропущен байт: {byte.hex()}")
        self._ready_state = False
        logging.info("Таймаут ожидания байта готовности")
        return False

    def _send_command(self, cmd: bytes, data: bytes = b'', expected_len: int = None) -> bytes:
        if not self.is_ready():
            logging.error("Весы не готовы к работе!")
            return b''
        try:
            self.ser.reset_input_buffer()
            logging.info(f"Отправка команды {cmd}, данные: {data.hex()}")
            
            buffer = b''
            counter = 0
            while self.ser.in_waiting == 0 and counter < 3:
                try:
                    self.ser.write(bytes.fromhex('01'))
                except serial.SerialException as e:
                    return None
                time.sleep(0.05)
                counter += 1

            while self.ser.in_waiting > 0:
                buffer += self.ser.read()
                time.sleep(0.01)

            if len(buffer) == 0:
                return None

            buffer = b''
            
            counter = 0
            while self.ser.in_waiting == 0 and counter < 3:
                try:
                    self.ser.write(cmd)
                    time.sleep(0.05)
                    if data:
                        self.ser.write(data)
                except serial.SerialException as e:
                    return None
                time.sleep(0.05)
                counter += 1

            buffer = b''
            while self.ser.in_waiting > 0:
                buffer += self.ser.read()
                time.sleep(0.01)
            self.ser.flush()
            
            response = buffer
            logging.info(f"{response.hex()}")
            if expected_len and expected_len > 0:
                if response and response[0:1] == b'\xEE':
                    logging.error("Ошибка выполнения команды (b'\\xEE')")
                    ready = self.ser.read(1)
                    if ready == b'\x80':
                        self._ready_state = True
                    return b'\xEE'
                ready = self.ser.read(1)
                if ready == b'\x80':
                    self._ready_state = True
                return response[1:]
            else:
                resp = response
                if resp == b'\xEE':
                    logging.error("Ошибка выполнения команды (b'\\xEE')")
                    ready = self.ser.read(1)
                    if ready == b'\x80':
                        self._ready_state = True
                    return b'\xEE'
                elif resp == b'\x80':
                    self._ready_state = True
                    return b''
                else:
                    self._ready_state = False
                    logging.error(f"Неожиданный ответ: {resp.hex()}")
                    return b'\xEE'
        except Exception as e:
            logging.error(f"Ошибка связи с весами: {str(e)}")
            self._ready_state = False
            return b''

    def _check_response(self, response: bytes, expected_len: int, context: str = "") -> bool:
        if not response or len(response) != expected_len:
            logging.error(f"Некорректный ответ {context}: {len(response) if response else 0} байт")
            return False
        return True

    # PLU Operations
    def get_plu_by_id(self, id: int) -> dict:
        if not self.is_ready():
            logging.error("Весы не готовы для чтения PLU")
            return {}
            
        id_bytes = id.to_bytes(4, 'little')
        response = self._send_command(cmd=COMMANDS["get_plu"], data=id_bytes, expected_len=LENGTHS['plu'])

        if response == ERROR_RESPONSE:
            return {}

        if not self._check_response(response, LENGTHS["plu"], "PLU"):
            return {}

        plu = {
            'id': int.from_bytes(response[0:4], 'little'),
            'code': self._bytes_to_str(response[4:10]),
            'name1': self._decode_name(response[10:38]),
            'name2': self._decode_name(response[38:66]),
            'price': int.from_bytes(response[66:70], 'little'),
            'expiry': self._parse_expiry(response[70:73]),
            'tare': int.from_bytes(response[73:75], 'little'),
            'group_code': self._bytes_to_str(response[75:81]),
            'message_number': int.from_bytes(response[81:83], 'little'),
            'last_reset': self.bcd_to_datetime(response[83:89]),
            'total_sum': int.from_bytes(response[89:93], 'little'),
            'total_weight': int.from_bytes(response[93:97], 'little'),
            'sales_count': int.from_bytes(response[97:100], 'little'),
        }

        return plu

    def create_plu(self, data: dict) -> bool:
        if not self.is_ready():
            logging.error("Весы не готовы для создания PLU")
            return False
            
        plu_bytes = self._encode_plu(data)
        response = self._send_command(cmd=COMMANDS["create_plu"], data=plu_bytes, expected_len=0)
        return response != ERROR_RESPONSE

    def _encode_plu(self, data: dict) -> bytes:
        expire_type = data.get('expiry_type')
        expiry = data.get('expiry_value')
        if expire_type == 0:
            day, month, year = map(int, expiry.split('.'))
            expiry_bytes = bytes([
                self._to_bcd(day),
                self._to_bcd(month),
                self._to_bcd(year)
            ])
        elif expire_type == 1:
            days = int(expiry)
            expiry_bytes = bytes([
                0x00,
                self._to_bcd(days // 100),
                self._to_bcd(days % 100)
            ])
        else:
            raise ValueError(f"expire_type должен быть 0 (дата) или 1 (дни)")

        parts = [
            data['id'].to_bytes(4, 'little'),
            self._str_to_bytes(data.get('code', '000000')),
            self._encode_name(data.get('name1', ''), data.get('logo_type', 0), data.get('cert_code', ''), 0),
            self._encode_name(data.get('name2', ''), data.get('logo_type', 0), data.get('cert_code', ''), 1),
            int(data['price']).to_bytes(4, 'little'),
            expiry_bytes,
            data.get('tare', 0).to_bytes(2, 'little'),
            self._str_to_bytes(data.get('group_code', '000000')),
            data.get('message_number', 0).to_bytes(2, 'little'),
        ]
        
        plu_bytes = b''.join(parts)
        if not self._check_response(plu_bytes, LENGTHS["plu_write"], "PLU Write"):
            raise ValueError("Invalid PLU length")
        
        return plu_bytes

    def _encode_name(self, text: str, logo_type: int, cert_code: str, line: int) -> bytes:
        max_len = 24 if logo_type else 28
        encoded = text.encode('cp866', errors='replace')[:max_len]
        padded = encoded.ljust(max_len, b'\x00')
        
        if logo_type:
            cert_bytes = self._encode_cert_code(cert_code, line, logo_type)
            return padded + cert_bytes
        return padded

    def _encode_cert_code(self, cert_code: str, line: int, logo_type: int) -> bytes:
        code = cert_code.ljust(4, '\x00')
        return bytes([
            0,
            logo_type,
            ord(code[3 - line]) if len(code) > (3 - line) else 0,
            ord(code[1 + line]) if len(code) > (1 + line) else 0
        ])

    def _decode_name(self, name_bytes: bytes) -> str:
        if name_bytes[24] == 0:
            raw_name = name_bytes[:24]
        else:
            raw_name = name_bytes[:28]
        return raw_name.split(b'\x00')[0].decode('cp866', errors='ignore')

    def _str_to_bytes(self, s: str) -> bytes:
        s = s.zfill(6)[:6]
        return bytes(int(ch) for ch in s)

    def _bytes_to_str(self, b: bytes) -> str:
        return ''.join(str(byte) for byte in b[::-1])

    def _parse_expiry(self, data: bytes):
        if len(data) != 3:
            return None

        def bcd_to_int(b):
            return ((b >> 4) * 10) + (b & 0x0F)

        if data[0] == 0:
            hundreds = bcd_to_int(data[1])
            tens_units = bcd_to_int(data[2])
            days = hundreds * 100 + tens_units
            return f"{days}"
        else:
            day = bcd_to_int(data[0])
            month = bcd_to_int(data[1])
            year = bcd_to_int(data[2])
            return f"{day:02d}.{month:02d}.{year:02d}"

    @staticmethod
    def _to_bcd(val):
        return ((val // 10) << 4) | (val % 10)

    def bcd_to_datetime(self, bcd_data):
        if len(bcd_data) != 6:
            return None
            
        second = (bcd_data[0] >> 4) * 10 + (bcd_data[0] & 0x0F)
        minute = (bcd_data[1] >> 4) * 10 + (bcd_data[1] & 0x0F)
        hour = (bcd_data[2] >> 4) * 10 + (bcd_data[2] & 0x0F)
        day = (bcd_data[3] >> 4) * 10 + (bcd_data[3] & 0x0F)
        month = (bcd_data[4] >> 4) * 10 + (bcd_data[4] & 0x0F)
        year = (bcd_data[5] >> 4) * 10 + (bcd_data[5] & 0x0F) + 2000
        
        try:
            return datetime(year, month, day, hour, minute, second)
        except ValueError:
            return None

    # Общие продажи
    def get_total_sales(self) -> dict:
        if not self.is_ready():
            logging.error("Весы не готовы для чтения продаж")
            return {}
            
        response = self._send_command(cmd=COMMANDS['get_total_sales'], expected_len=LENGTHS['total_sales'])
        if response == ERROR_RESPONSE:
            return {}

        if not self._check_response(response, LENGTHS['total_sales'], 'Total sales read'):
            return {}
    
        return {
            'mileage': int.from_bytes(response[0:4], 'little'),
            'label_count': int.from_bytes(response[4:8], 'little'),
            'total_sum': int.from_bytes(response[8:12], 'little'),
            'sales_count': int.from_bytes(response[12:15], 'little'),
            'total_weight': int.from_bytes(response[15:19], 'little'),
            'plu_sum': int.from_bytes(response[19:23], 'little'),
            'plu_sales_count': int.from_bytes(response[23:26], 'little'),
            'plu_weight': int.from_bytes(response[26:30], 'little'),
            'free_plu': int.from_bytes(response[36:38], 'little'),
            'free_msg': int.from_bytes(response[38:40], 'little'),
        }

    def reset_total_sales(self) -> bool:
        if not self.is_ready():
            logging.error("Весы не готовы для сброса продаж")
            return False
            
        response = self._send_command(cmd=COMMANDS['reset_total_sales'], expected_len=0)
        return response != ERROR_RESPONSE

    # Текущее состояние весов
    def get_current_status(self) -> dict:
        if not self.is_ready():
            logging.error("Весы не готовы для чтения статуса")
            return {}
            
        response = self._send_command(cmd=COMMANDS['get_status'], expected_len=LENGTHS['current_status'])
        if response == ERROR_RESPONSE:
            return {}
        
        if not self._check_response(response, LENGTHS['current_status'], 'Current status read'):
            return {}
        
        data = response
        status = data[0]
        abs_weight = int.from_bytes(data[1:3], "little")
        if status & 0b10000000:
            weight = -abs_weight
        else:
            weight = abs_weight

        return {
            "status_byte": status,
            "weight": weight,
            "price": int.from_bytes(data[3:7], "little"),
            "sum": int.from_bytes(data[7:11], "little"),
            "plu_number": int.from_bytes(data[11:15], "little"),
            "bits": {
                "overload": bool(status & 0b00000001),
                "tare_mode": bool(status & 0b00000100),
                "zero_weight": bool(status & 0b00001000),
                "dual_range": bool(status & 0b00100000),
                "stable_weight": bool(status & 0b01000000),
                "minus_sign": bool(status & 0b10000000),
            }
        }

# API функции
def get_command():
    url = f"{SERVER_URL}/api/commands/{CLIENT_ID}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logging.error(f"Ошибка при получении команды: {e}")
        return None

def send_data(data_type, data):
    url = f"{SERVER_URL}/api/data/{CLIENT_ID}"
    payload = {'data_type': data_type, 'data': data}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logging.error(f"Ошибка при отправке данных: {e}")
        return None

def send_plu_data(plu_list):
    url = f"{SERVER_URL}/api/plu_upload/{CLIENT_ID}"
    payload = {'plu_list': plu_list}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logging.error(f"Ошибка при отправке PLU данных: {e}")
        return None

def ack_command(command_id):
    url = f"{SERVER_URL}/api/ack/{CLIENT_ID}"
    payload = {'command_id': command_id}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logging.error(f"Ошибка при подтверждении команды: {e}")
        return None

def send_status(scale_client):
    status_data = {
        'scales_connected': scale_client.is_ready(),
        'port': scale_client.port,
        'connection_attempts': scale_client._connection_attempts,
        'timestamp': datetime.now().isoformat()
    }
    send_data('scales_status', json.dumps(status_data, ensure_ascii=False))

def execute_command(command_data, scale_client):
    try:
        command = json.loads(command_data)
        action = command.get('action')
        
        if action == 'upload_plu':
            if not scale_client.is_ready():
                return {'result': 'error', 'message': 'Весы не подключены'}
                
            plu_list = command.get('data', [])
            success_count = 0
            for plu in plu_list:
                scale_plu = {
                    'id': plu['number'],
                    'name1': plu['name1'],
                    'name2': plu.get('name2', ''),
                    'price': int(float(plu['price']) * 100),
                    'code': plu.get('code', '000000'),
                    'group_code': plu.get('group_code', '000000'),
                    'tare': plu.get('tare', 0),
                    'message_number': plu.get('message_number', 0),
                    'expiry_type': plu.get('expiry_type', 0),
                    'expiry_value': plu.get('expiry_value', '01.01.25'),
                    'logo_type': plu.get('logo_type', 0),
                    'cert_code': plu.get('cert_code', '')
                }
                if scale_client.create_plu(scale_plu):
                    success_count += 1
                    logging.info(f"Товар {plu['number']} загружен в весы")
                else:
                    logging.error(f"Ошибка загрузки товара {plu['number']} в весы")
            
            return {'result': 'ok', 'uploaded_count': success_count, 'total_count': len(plu_list)}
            
        elif action == 'download_plu':
            if not scale_client.is_ready():
                return {'result': 'error', 'message': 'Весы не подключены'}
                
            numbers = command.get('numbers', [])
            plu_list = []
            for number in numbers:
                plu = scale_client.get_plu_by_id(number)
                if plu:
                    server_plu = {
                        'number': plu['id'],
                        'name1': plu['name1'],
                        'name2': plu['name2'],
                        'price': plu['price'] / 100.0,
                        'code': plu['code'],
                        'group_code': plu['group_code'],
                        'tare': plu['tare'],
                        'message_number': plu['message_number'],
                        'expiry_type': 0 if '.' in str(plu['expiry']) else 1,
                        'expiry_value': plu['expiry'],
                        'logo_type': 0,
                        'cert_code': ''
                    }
                    plu_list.append(server_plu)
                    logging.info(f"Товар {number} загружен из весов")
                else:
                    logging.warning(f"Товар {number} не найден в весах")
            
            if plu_list:
                send_plu_data(plu_list)
            
            return {'result': 'ok', 'downloaded_count': len(plu_list), 'total_count': len(numbers)}
            
        elif action == 'get_status':
            if not scale_client.is_ready():
                return {'result': 'error', 'message': 'Весы не подключены'}
                
            status = scale_client.get_current_status()
            send_data('current_status', json.dumps(status, ensure_ascii=False))
            return {'result': 'ok', 'status': status}
            
        elif action == 'get_total_sales':
            if not scale_client.is_ready():
                return {'result': 'error', 'message': 'Весы не подключены'}
                
            sales = scale_client.get_total_sales()
            send_data('total_sales', json.dumps(sales, ensure_ascii=False))
            return {'result': 'ok', 'sales': sales}
            
        elif action == 'reset_total_sales':
            if not scale_client.is_ready():
                return {'result': 'error', 'message': 'Весы не подключены'}
                
            success = scale_client.reset_total_sales()
            return {'result': 'ok' if success else 'error', 'message': 'Продажи сброшены' if success else 'Ошибка сброса'}
            
        else:
            logging.warning(f"Неизвестная команда: {action}")
            return {'result': 'unknown_command'}
            
    except Exception as e:
        logging.error(f"Ошибка выполнения команды: {e}")
        return {'result': 'error', 'message': str(e)}

def main():
    logging.info(f"Клиент {CLIENT_ID} запущен. Опрос сервера {SERVER_URL}")
    
    scale_client = ScaleClient()
    send_status(scale_client)
    
    try:
        while True:
            if not scale_client.is_ready():
                scale_client.try_reconnect()
                send_status(scale_client)
            
            cmd_resp = get_command()
            if cmd_resp and cmd_resp.get('command'):
                command = cmd_resp['command']
                command_id = cmd_resp['command_id']
                
                logging.info(f"Получена команда: {command}")
                result = execute_command(command, scale_client)
                
                send_data('command_result', json.dumps(result, ensure_ascii=False))
                ack_command(command_id)
                
                logging.info(f"Команда выполнена: {result}")
            
            time.sleep(POLL_INTERVAL)
            
    except KeyboardInterrupt:
        logging.info("Клиент остановлен пользователем")
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
    finally:
        scale_client.disconnect()

if __name__ == '__main__':
    main() 