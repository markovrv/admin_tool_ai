from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///admin_server.db'
app.secret_key = 'your-secret-key-here'  # Для flash сообщений
db = SQLAlchemy(app)

# --- Модели ---
class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(64), unique=True, nullable=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

class Command(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(64), db.ForeignKey('client.client_id'))
    command = db.Column(db.String(256), nullable=False)
    status = db.Column(db.String(32), default='pending')  # pending, sent, done
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ClientData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(64), db.ForeignKey('client.client_id'))
    data_type = db.Column(db.String(64))
    data = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PLU(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, unique=True, nullable=False)
    name1 = db.Column(db.String(28), nullable=False)  # Название строка 1
    name2 = db.Column(db.String(28), default='')      # Название строка 2
    price = db.Column(db.Float, nullable=False)       # Цена в рублях
    code = db.Column(db.String(6), default='000000')  # Код товара (6 цифр)
    group_code = db.Column(db.String(6), default='000000')  # Групповой код
    tare = db.Column(db.Integer, default=0)           # Тара в граммах
    message_number = db.Column(db.Integer, default=0) # Номер сообщения
    expiry_type = db.Column(db.Integer, default=0)    # Тип срока годности (0-дата, 1-дни)
    expiry_value = db.Column(db.String(10), default='01.01.25')  # Срок годности
    logo_type = db.Column(db.Integer, default=0)      # Тип логотипа
    cert_code = db.Column(db.String(4), default='')   # Сертификационный код

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, unique=True, nullable=False)  # Номер сообщения
    content = db.Column(db.Text, nullable=False)  # Содержимое сообщения
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(64), db.ForeignKey('client.client_id'))
    dept_no = db.Column(db.Integer, default=1)  # Номер отдела
    label_format = db.Column(db.Integer, default=0)  # Формат этикетки
    barcode_format = db.Column(db.Integer, default=0)  # Формат штрих-кода
    adjst = db.Column(db.Integer, default=0)  # Настройка
    print_features = db.Column(db.Integer, default=0)  # Особенности печати
    auto_print_weight = db.Column(db.Integer, default=0)  # Автопечать веса
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class FactorySettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(64), db.ForeignKey('client.client_id'))
    max_weight = db.Column(db.Integer, default=15000)  # Максимальный вес
    dec_point_weight = db.Column(db.Integer, default=2)  # Знаков после запятой для веса
    dec_point_price = db.Column(db.Integer, default=2)  # Знаков после запятой для цены
    dec_point_sum = db.Column(db.Integer, default=2)  # Знаков после запятой для суммы
    dual_range = db.Column(db.Integer, default=0)  # Двойной диапазон
    weight_step_upper = db.Column(db.Integer, default=10)  # Шаг веса верхний диапазон
    weight_step_lower = db.Column(db.Integer, default=5)  # Шаг веса нижний диапазон
    price_weight = db.Column(db.Integer, default=0)  # Цена за вес
    round_sum = db.Column(db.Integer, default=0)  # Округление суммы
    tare_limit = db.Column(db.Integer, default=5000)  # Лимит тары
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TotalSales(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(64), db.ForeignKey('client.client_id'))
    mileage = db.Column(db.Integer, default=0)  # Пробег
    label_count = db.Column(db.Integer, default=0)  # Количество этикеток
    total_sum = db.Column(db.Integer, default=0)  # Общая сумма
    sales_count = db.Column(db.Integer, default=0)  # Количество продаж
    total_weight = db.Column(db.Integer, default=0)  # Общий вес
    plu_sum = db.Column(db.Integer, default=0)  # Сумма PLU
    plu_sales_count = db.Column(db.Integer, default=0)  # Количество продаж PLU
    plu_weight = db.Column(db.Integer, default=0)  # Вес PLU
    free_plu = db.Column(db.Integer, default=0)  # Свободные PLU
    free_msg = db.Column(db.Integer, default=0)  # Свободные сообщения
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ScaleStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(64), db.ForeignKey('client.client_id'))
    status_byte = db.Column(db.Integer, default=0)  # Байт статуса
    weight = db.Column(db.Integer, default=0)  # Вес
    price = db.Column(db.Integer, default=0)  # Цена
    sum = db.Column(db.Integer, default=0)  # Сумма
    plu_number = db.Column(db.Integer, default=0)  # Номер PLU
    overload = db.Column(db.Boolean, default=False)  # Перегрузка
    tare_mode = db.Column(db.Boolean, default=False)  # Режим тары
    zero_weight = db.Column(db.Boolean, default=False)  # Нулевой вес
    dual_range = db.Column(db.Boolean, default=False)  # Двойной диапазон
    stable_weight = db.Column(db.Boolean, default=False)  # Стабильный вес
    minus_sign = db.Column(db.Boolean, default=False)  # Минусовый знак
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- API ---
@app.route('/api/commands/<client_id>', methods=['GET'])
def get_command(client_id):
    client = Client.query.filter_by(client_id=client_id).first()
    if not client:
        client = Client(client_id=client_id)
        db.session.add(client)
        db.session.commit()
    client.last_seen = datetime.utcnow()
    db.session.commit()
    command = Command.query.filter_by(client_id=client_id, status='pending').first()
    if command:
        command.status = 'sent'
        db.session.commit()
        return jsonify({'command': command.command, 'command_id': command.id})
    return jsonify({'command': None})

@app.route('/api/data/<client_id>', methods=['POST'])
def post_data(client_id):
    content = request.json
    data_type = content.get('data_type')
    data = content.get('data')
    client = Client.query.filter_by(client_id=client_id).first()
    if not client:
        return jsonify({'error': 'Unknown client'}), 404
    
    # Сохраняем данные в ClientData
    client_data = ClientData(client_id=client_id, data_type=data_type, data=data)
    db.session.add(client_data)
    
    # Обрабатываем специальные типы данных
    if data_type == 'current_status':
        try:
            status_data = json.loads(data)
            scale_status = ScaleStatus(
                client_id=client_id,
                status_byte=status_data.get('status_byte', 0),
                weight=status_data.get('weight', 0),
                price=status_data.get('price', 0),
                sum=status_data.get('sum', 0),
                plu_number=status_data.get('plu_number', 0),
                overload=status_data.get('bits', {}).get('overload', False),
                tare_mode=status_data.get('bits', {}).get('tare_mode', False),
                zero_weight=status_data.get('bits', {}).get('zero_weight', False),
                dual_range=status_data.get('bits', {}).get('dual_range', False),
                stable_weight=status_data.get('bits', {}).get('stable_weight', False),
                minus_sign=status_data.get('bits', {}).get('minus_sign', False)
            )
            db.session.add(scale_status)
        except Exception as e:
            print(f"Ошибка обработки статуса: {e}")
    
    elif data_type == 'total_sales':
        try:
            sales_data = json.loads(data)
            total_sales = TotalSales(
                client_id=client_id,
                mileage=sales_data.get('mileage', 0),
                label_count=sales_data.get('label_count', 0),
                total_sum=sales_data.get('total_sum', 0),
                sales_count=sales_data.get('sales_count', 0),
                total_weight=sales_data.get('total_weight', 0),
                plu_sum=sales_data.get('plu_sum', 0),
                plu_sales_count=sales_data.get('plu_sales_count', 0),
                plu_weight=sales_data.get('plu_weight', 0),
                free_plu=sales_data.get('free_plu', 0),
                free_msg=sales_data.get('free_msg', 0)
            )
            db.session.add(total_sales)
        except Exception as e:
            print(f"Ошибка обработки продаж: {e}")
    
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/ack/<client_id>', methods=['POST'])
def ack_command(client_id):
    content = request.json
    command_id = content.get('command_id')
    command = Command.query.filter_by(id=command_id, client_id=client_id).first()
    if command:
        command.status = 'done'
        db.session.commit()
        return jsonify({'status': 'acknowledged'})
    return jsonify({'error': 'Command not found'}), 404

# --- API для загрузки данных от клиентов ---
@app.route('/api/plu_upload/<client_id>', methods=['POST'])
def api_plu_upload(client_id):
    content = request.json
    plu_list = content.get('plu_list', [])
    for plu in plu_list:
        number = plu.get('number')
        name1 = plu.get('name1', '')
        name2 = plu.get('name2', '')
        price = plu.get('price')
        code = plu.get('code', '000000')
        group_code = plu.get('group_code', '000000')
        tare = plu.get('tare', 0)
        message_number = plu.get('message_number', 0)
        expiry_type = plu.get('expiry_type', 0)
        expiry_value = plu.get('expiry_value', '01.01.25')
        logo_type = plu.get('logo_type', 0)
        cert_code = plu.get('cert_code', '')
        
        if number and name1 and price is not None:
            existing = PLU.query.filter_by(number=number).first()
            if existing:
                existing.name1 = name1
                existing.name2 = name2
                existing.price = price
                existing.code = code
                existing.group_code = group_code
                existing.tare = tare
                existing.message_number = message_number
                existing.expiry_type = expiry_type
                existing.expiry_value = expiry_value
                existing.logo_type = logo_type
                existing.cert_code = cert_code
            else:
                new_plu = PLU(
                    number=number, name1=name1, name2=name2, price=price,
                    code=code, group_code=group_code, tare=tare,
                    message_number=message_number, expiry_type=expiry_type,
                    expiry_value=expiry_value, logo_type=logo_type, cert_code=cert_code
                )
                db.session.add(new_plu)
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/message_upload/<client_id>', methods=['POST'])
def api_message_upload(client_id):
    content = request.json
    message_list = content.get('message_list', [])
    for msg in message_list:
        number = msg.get('id')
        content_text = msg.get('content', '')
        
        if number and content_text:
            existing = Message.query.filter_by(number=number).first()
            if existing:
                existing.content = content_text
            else:
                new_msg = Message(number=number, content=content_text)
                db.session.add(new_msg)
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/settings_upload/<client_id>', methods=['POST'])
def api_settings_upload(client_id):
    content = request.json
    settings_type = content.get('settings_type')
    settings_data = content.get('settings_data', {})
    
    if settings_type == 'user':
        existing = UserSettings.query.filter_by(client_id=client_id).first()
        if existing:
            existing.dept_no = settings_data.get('dept_no', 1)
            existing.label_format = settings_data.get('label_format', 0)
            existing.barcode_format = settings_data.get('barcode_format', 0)
            existing.adjst = settings_data.get('adjst', 0)
            existing.print_features = settings_data.get('print_features', 0)
            existing.auto_print_weight = settings_data.get('auto_print_weight', 0)
        else:
            new_settings = UserSettings(
                client_id=client_id,
                dept_no=settings_data.get('dept_no', 1),
                label_format=settings_data.get('label_format', 0),
                barcode_format=settings_data.get('barcode_format', 0),
                adjst=settings_data.get('adjst', 0),
                print_features=settings_data.get('print_features', 0),
                auto_print_weight=settings_data.get('auto_print_weight', 0)
            )
            db.session.add(new_settings)
    
    elif settings_type == 'factory':
        existing = FactorySettings.query.filter_by(client_id=client_id).first()
        if existing:
            existing.max_weight = settings_data.get('max_weight', 15000)
            existing.dec_point_weight = settings_data.get('dec_point_weight', 2)
            existing.dec_point_price = settings_data.get('dec_point_price', 2)
            existing.dec_point_sum = settings_data.get('dec_point_sum', 2)
            existing.dual_range = settings_data.get('dual_range', 0)
            existing.weight_step_upper = settings_data.get('weight_step_upper', 10)
            existing.weight_step_lower = settings_data.get('weight_step_lower', 5)
            existing.price_weight = settings_data.get('price_weight', 0)
            existing.round_sum = settings_data.get('round_sum', 0)
            existing.tare_limit = settings_data.get('tare_limit', 5000)
        else:
            new_settings = FactorySettings(
                client_id=client_id,
                max_weight=settings_data.get('max_weight', 15000),
                dec_point_weight=settings_data.get('dec_point_weight', 2),
                dec_point_price=settings_data.get('dec_point_price', 2),
                dec_point_sum=settings_data.get('dec_point_sum', 2),
                dual_range=settings_data.get('dual_range', 0),
                weight_step_upper=settings_data.get('weight_step_upper', 10),
                weight_step_lower=settings_data.get('weight_step_lower', 5),
                price_weight=settings_data.get('price_weight', 0),
                round_sum=settings_data.get('round_sum', 0),
                tare_limit=settings_data.get('tare_limit', 5000)
            )
            db.session.add(new_settings)
    
    db.session.commit()
    return jsonify({'status': 'ok'})

# --- Веб-интерфейс ---
@app.route('/')
def index():
    clients = Client.query.all()
    # Получаем последние статусы весов для каждого клиента
    for client in clients:
        latest_status = ClientData.query.filter_by(
            client_id=client.client_id, 
            data_type='scales_status'
        ).order_by(ClientData.created_at.desc()).first()
        
        if latest_status:
            try:
                status_data = json.loads(latest_status.data)
                client.scales_connected = status_data.get('scales_connected', False)
                client.connection_attempts = status_data.get('connection_attempts', 0)
                client.last_status_time = latest_status.created_at
            except:
                client.scales_connected = False
                client.connection_attempts = 0
        else:
            client.scales_connected = False
            client.connection_attempts = 0
    
    return render_template('index.html', clients=clients)

@app.route('/commands/<client_id>')
def commands(client_id):
    commands = Command.query.filter_by(client_id=client_id).order_by(Command.created_at.desc()).all()
    return render_template('commands.html', commands=commands, client_id=client_id)

@app.route('/data/<client_id>')
def data(client_id):
    data = ClientData.query.filter_by(client_id=client_id).order_by(ClientData.created_at.desc()).all()
    return render_template('data.html', data=data, client_id=client_id)

@app.route('/send_command/<client_id>', methods=['GET', 'POST'])
def send_command(client_id):
    if request.method == 'POST':
        command_text = request.form.get('command')
        if command_text:
            command = Command(client_id=client_id, command=command_text)
            db.session.add(command)
            db.session.commit()
            flash(f'Команда "{command_text}" отправлена клиенту {client_id}', 'success')
            return redirect(url_for('commands', client_id=client_id))
        else:
            flash('Команда не может быть пустой', 'error')
    
    return render_template('send_command.html', client_id=client_id)

# --- Веб-интерфейс для PLU ---
@app.route('/plu')
def plu_list():
    plus = PLU.query.order_by(PLU.number).all()
    clients = Client.query.all()
    return render_template('plu_list.html', plus=plus, clients=clients)

@app.route('/plu/select_client/<action>')
def select_client_for_plu(action):
    """Страница выбора клиента для операций с товарами"""
    clients = Client.query.all()
    return render_template('select_client.html', clients=clients, action=action)

@app.route('/plu/add', methods=['GET', 'POST'])
def plu_add():
    if request.method == 'POST':
        number = request.form.get('number', type=int)
        name1 = request.form.get('name1')
        name2 = request.form.get('name2', '')
        price = request.form.get('price', type=float)
        code = request.form.get('code', '000000')
        group_code = request.form.get('group_code', '000000')
        tare = request.form.get('tare', type=int) or 0
        message_number = request.form.get('message_number', type=int) or 0
        expiry_type = request.form.get('expiry_type', type=int) or 0
        expiry_value = request.form.get('expiry_value', '01.01.25')
        logo_type = request.form.get('logo_type', type=int) or 0
        cert_code = request.form.get('cert_code', '')
        
        if number and name1 and price is not None:
            if PLU.query.filter_by(number=number).first():
                flash('Товар с таким номером уже существует', 'danger')
            else:
                plu = PLU(
                    number=number, name1=name1, name2=name2, price=price,
                    code=code, group_code=group_code, tare=tare,
                    message_number=message_number, expiry_type=expiry_type,
                    expiry_value=expiry_value, logo_type=logo_type, cert_code=cert_code
                )
                db.session.add(plu)
                db.session.commit()
                flash('Товар добавлен', 'success')
                return redirect(url_for('plu_list'))
        else:
            flash('Заполните обязательные поля (номер, название, цена)', 'danger')
    return render_template('plu_form.html', action='add')

@app.route('/plu/edit/<int:plu_id>', methods=['GET', 'POST'])
def plu_edit(plu_id):
    plu = PLU.query.get_or_404(plu_id)
    if request.method == 'POST':
        plu.number = request.form.get('number', type=int)
        plu.name1 = request.form.get('name1')
        plu.name2 = request.form.get('name2', '')
        plu.price = request.form.get('price', type=float)
        plu.code = request.form.get('code', '000000')
        plu.group_code = request.form.get('group_code', '000000')
        plu.tare = request.form.get('tare', type=int) or 0
        plu.message_number = request.form.get('message_number', type=int) or 0
        plu.expiry_type = request.form.get('expiry_type', type=int) or 0
        plu.expiry_value = request.form.get('expiry_value', '01.01.25')
        plu.logo_type = request.form.get('logo_type', type=int) or 0
        plu.cert_code = request.form.get('cert_code', '')
        
        db.session.commit()
        flash('Товар обновлен', 'success')
        return redirect(url_for('plu_list'))
    return render_template('plu_form.html', action='edit', plu=plu)

@app.route('/plu/delete/<int:plu_id>', methods=['POST'])
def plu_delete(plu_id):
    plu = PLU.query.get_or_404(plu_id)
    db.session.delete(plu)
    db.session.commit()
    flash('Товар удален', 'success')
    return redirect(url_for('plu_list'))

# --- Кнопки для обмена с весами ---
@app.route('/plu/send_to_scales/<client_id>', methods=['GET', 'POST'])
def send_to_scales(client_id):
    plus = PLU.query.all()
    plu_data = []
    for p in plus:
        plu_data.append({
            'number': p.number,
            'name1': p.name1,
            'name2': p.name2,
            'price': p.price,
            'code': p.code,
            'group_code': p.group_code,
            'tare': p.tare,
            'message_number': p.message_number,
            'expiry_type': p.expiry_type,
            'expiry_value': p.expiry_value,
            'logo_type': p.logo_type,
            'cert_code': p.cert_code
        })
    command = Command(client_id=client_id, command=json.dumps({'action': 'upload_plu', 'data': plu_data}))
    db.session.add(command)
    db.session.commit()
    flash(f'Товары отправлены клиенту {client_id}', 'success')
    return redirect(url_for('plu_list'))

@app.route('/plu/load_from_scales_form/<client_id>', methods=['GET', 'POST'])
def load_from_scales_form(client_id):
    """Форма для загрузки товаров из весов с указанием номеров"""
    if request.method == 'POST':
        numbers = request.form.get('numbers')
        if not numbers:
            flash('Укажите номера товаров через запятую', 'danger')
            return redirect(url_for('load_from_scales_form', client_id=client_id))
        try:
            num_list = [int(n.strip()) for n in numbers.split(',') if n.strip().isdigit()]
        except Exception:
            flash('Некорректный формат номеров', 'danger')
            return redirect(url_for('load_from_scales_form', client_id=client_id))
        command = Command(client_id=client_id, command=json.dumps({'action': 'download_plu', 'numbers': num_list}))
        db.session.add(command)
        db.session.commit()
        flash(f'Команда на загрузку товаров отправлена клиенту {client_id}', 'success')
        return redirect(url_for('plu_list'))
    
    return render_template('load_from_scales_form.html', client_id=client_id)

# --- Веб-интерфейс для сообщений ---
@app.route('/messages')
def message_list():
    messages = Message.query.order_by(Message.number).all()
    clients = Client.query.all()
    return render_template('message_list.html', messages=messages, clients=clients)

@app.route('/messages/add', methods=['GET', 'POST'])
def message_add():
    if request.method == 'POST':
        number = request.form.get('number', type=int)
        content = request.form.get('content')
        
        if number and content:
            if Message.query.filter_by(number=number).first():
                flash('Сообщение с таким номером уже существует', 'danger')
            else:
                message = Message(number=number, content=content)
                db.session.add(message)
                db.session.commit()
                flash('Сообщение добавлено', 'success')
                return redirect(url_for('message_list'))
        else:
            flash('Заполните обязательные поля (номер, содержимое)', 'danger')
    return render_template('message_form.html', action='add')

@app.route('/messages/edit/<int:message_id>', methods=['GET', 'POST'])
def message_edit(message_id):
    message = Message.query.get_or_404(message_id)
    if request.method == 'POST':
        message.number = request.form.get('number', type=int)
        message.content = request.form.get('content')
        db.session.commit()
        flash('Сообщение обновлено', 'success')
        return redirect(url_for('message_list'))
    return render_template('message_form.html', action='edit', message=message)

@app.route('/messages/delete/<int:message_id>', methods=['POST'])
def message_delete(message_id):
    message = Message.query.get_or_404(message_id)
    db.session.delete(message)
    db.session.commit()
    flash('Сообщение удалено', 'success')
    return redirect(url_for('message_list'))

# --- Веб-интерфейс для настроек ---
@app.route('/settings/<client_id>')
def settings_view(client_id):
    user_settings = UserSettings.query.filter_by(client_id=client_id).first()
    factory_settings = FactorySettings.query.filter_by(client_id=client_id).first()
    return render_template('settings.html', client_id=client_id, 
                         user_settings=user_settings, factory_settings=factory_settings)

@app.route('/settings/user/<client_id>', methods=['GET', 'POST'])
def user_settings_edit(client_id):
    settings = UserSettings.query.filter_by(client_id=client_id).first()
    if not settings:
        settings = UserSettings(client_id=client_id)
        db.session.add(settings)
        db.session.commit()
    
    if request.method == 'POST':
        settings.dept_no = request.form.get('dept_no', type=int) or 1
        settings.label_format = request.form.get('label_format', type=int) or 0
        settings.barcode_format = request.form.get('barcode_format', type=int) or 0
        settings.adjst = request.form.get('adjst', type=int) or 0
        settings.print_features = request.form.get('print_features', type=int) or 0
        settings.auto_print_weight = request.form.get('auto_print_weight', type=int) or 0
        db.session.commit()
        flash('Настройки пользователя обновлены', 'success')
        return redirect(url_for('settings_view', client_id=client_id))
    
    return render_template('user_settings_form.html', client_id=client_id, settings=settings)

@app.route('/settings/factory/<client_id>', methods=['GET', 'POST'])
def factory_settings_edit(client_id):
    settings = FactorySettings.query.filter_by(client_id=client_id).first()
    if not settings:
        settings = FactorySettings(client_id=client_id)
        db.session.add(settings)
        db.session.commit()
    
    if request.method == 'POST':
        settings.max_weight = request.form.get('max_weight', type=int) or 15000
        settings.dec_point_weight = request.form.get('dec_point_weight', type=int) or 2
        settings.dec_point_price = request.form.get('dec_point_price', type=int) or 2
        settings.dec_point_sum = request.form.get('dec_point_sum', type=int) or 2
        settings.dual_range = request.form.get('dual_range', type=int) or 0
        settings.weight_step_upper = request.form.get('weight_step_upper', type=int) or 10
        settings.weight_step_lower = request.form.get('weight_step_lower', type=int) or 5
        settings.price_weight = request.form.get('price_weight', type=int) or 0
        settings.round_sum = request.form.get('round_sum', type=int) or 0
        settings.tare_limit = request.form.get('tare_limit', type=int) or 5000
        db.session.commit()
        flash('Заводские настройки обновлены', 'success')
        return redirect(url_for('settings_view', client_id=client_id))
    
    return render_template('factory_settings_form.html', client_id=client_id, settings=settings)

# --- Веб-интерфейс для продаж ---
@app.route('/sales/<client_id>')
def sales_view(client_id):
    sales = TotalSales.query.filter_by(client_id=client_id).order_by(TotalSales.created_at.desc()).limit(10).all()
    return render_template('sales.html', client_id=client_id, sales=sales)

# --- Веб-интерфейс для статуса весов ---
@app.route('/status/<client_id>')
def status_view(client_id):
    statuses = ScaleStatus.query.filter_by(client_id=client_id).order_by(ScaleStatus.created_at.desc()).limit(10).all()
    return render_template('status.html', client_id=client_id, statuses=statuses)

# --- Команды для весов ---
@app.route('/send_scale_command/<client_id>', methods=['GET', 'POST'])
def send_scale_command(client_id):
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'get_status':
            command = Command(client_id=client_id, command=json.dumps({'action': 'get_status'}))
        elif action == 'get_total_sales':
            command = Command(client_id=client_id, command=json.dumps({'action': 'get_total_sales'}))
        elif action == 'reset_total_sales':
            command = Command(client_id=client_id, command=json.dumps({'action': 'reset_total_sales'}))
        elif action == 'get_user_settings':
            command = Command(client_id=client_id, command=json.dumps({'action': 'get_user_settings'}))
        elif action == 'get_factory_settings':
            command = Command(client_id=client_id, command=json.dumps({'action': 'get_factory_settings'}))
        else:
            flash('Неизвестная команда', 'error')
            return redirect(url_for('send_scale_command', client_id=client_id))
        
        db.session.add(command)
        db.session.commit()
        flash(f'Команда "{action}" отправлена клиенту {client_id}', 'success')
        return redirect(url_for('send_scale_command', client_id=client_id))
    
    return render_template('send_scale_command.html', client_id=client_id)

@app.route('/plu/send_selected_to_scales', methods=['POST'])
def send_selected_to_scales():
    selected_numbers = request.form.getlist('selected_plus')
    if not selected_numbers:
        flash('Выберите хотя бы один товар для отправки', 'danger')
        return redirect(url_for('plu_list'))
    # Сохраняем выбранные номера во временную сессию
    # Можно использовать session, но для простоты — через query string
    return redirect(url_for('select_client_for_selected', numbers=','.join(selected_numbers)))

@app.route('/plu/select_client_for_selected')
def select_client_for_selected():
    numbers = request.args.get('numbers', '')
    clients = Client.query.all()
    return render_template('select_client.html', clients=clients, action='send_selected', numbers=numbers)

@app.route('/plu/send_selected_to_scales_final/<client_id>/<numbers>')
def send_selected_to_scales_final(client_id, numbers):
    num_list = [int(n) for n in numbers.split(',') if n.isdigit()]
    plus = PLU.query.filter(PLU.number.in_(num_list)).all()
    plu_data = []
    for p in plus:
        plu_data.append({
            'number': p.number,
            'name1': p.name1,
            'name2': p.name2,
            'price': p.price,
            'code': p.code,
            'group_code': p.group_code,
            'tare': p.tare,
            'message_number': p.message_number,
            'expiry_type': p.expiry_type,
            'expiry_value': p.expiry_value,
            'logo_type': p.logo_type,
            'cert_code': p.cert_code
        })
    command = Command(client_id=client_id, command=json.dumps({'action': 'upload_plu', 'data': plu_data}))
    db.session.add(command)
    db.session.commit()
    flash(f'Выбранные товары отправлены клиенту {client_id}', 'success')
    return redirect(url_for('plu_list'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000) 