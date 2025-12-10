from flask import Flask, request, redirect, url_for, send_file, flash, render_template_string
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import io
import os
import re

# ==================================
# 1. 初始化和配置
# ==================================
app = Flask(__name__)
DB_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'address_book.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SECRET_KEY'] = 'your_final_secret_key'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
db = SQLAlchemy(app)


# ==================================
# 工具函数：提取中文拼音首字母
# ==================================
def get_first_letter(name):
    if not name:
        return '?'

    ch = name[0]

    # 英文
    if ch.encode('UTF-8').isalpha():
        return ch.upper()

    # 中文 GBK 首字母区间
    gbk = ch.encode('gbk', errors='ignore')
    if len(gbk) == 2:
        asc = gbk[0] * 256 + gbk[1]
        if 45217 <= asc <= 45252: return 'A'
        if 45253 <= asc <= 45760: return 'B'
        if 45761 <= asc <= 46317: return 'C'
        if 46318 <= asc <= 46825: return 'D'
        if 46826 <= asc <= 47009: return 'E'
        if 47010 <= asc <= 47296: return 'F'
        if 47297 <= asc <= 47613: return 'G'
        if 47614 <= asc <= 48118: return 'H'
        if 48119 <= asc <= 49061: return 'J'
        if 49062 <= asc <= 49323: return 'K'
        if 49324 <= asc <= 49895: return 'L'
        if 49896 <= asc <= 50370: return 'M'
        if 50371 <= asc <= 50613: return 'N'
        if 50614 <= asc <= 50621: return 'O'
        if 50622 <= asc <= 50905: return 'P'
        if 50906 <= asc <= 51386: return 'Q'
        if 51387 <= asc <= 51445: return 'R'
        if 51446 <= asc <= 52217: return 'S'
        if 52218 <= asc <= 52697: return 'T'
        if 52698 <= asc <= 52979: return 'W'
        if 52980 <= asc <= 53688: return 'X'
        if 53689 <= asc <= 54480: return 'Y'
        if 54481 <= asc <= 55289: return 'Z'
    return '?'


# ==================================
# 2. 数据库模型定义（新增 group / photo / first_letter）
# ==================================
class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    is_bookmarked = db.Column(db.Boolean, default=False)

    group = db.Column(db.String(50), default="未分组")  # 新增：分组
    photo_path = db.Column(db.String(200), default=None)  # 新增：头像
    first_letter = db.Column(db.String(1), default='?')  # 新增：拼音首字母

    methods = db.relationship('ContactMethod', backref='contact',
                              lazy='dynamic', cascade="all, delete-orphan")


class ContactMethod(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    method_type = db.Column(db.String(50), nullable=False)
    value = db.Column(db.String(200), nullable=False)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'), nullable=False)


# ==================================
# 3. 路由
# ==================================
@app.route('/')
def index():
    contacts = Contact.query.order_by(
        Contact.is_bookmarked.desc(),
        Contact.group.asc(),
        Contact.first_letter.asc(),
        Contact.name.asc()
    ).all()

    full_html = BASE_HTML.replace('{% block content %}{% endblock %}', INDEX_HTML_CONTENT)
    return render_template_string(full_html, contacts=contacts)


@app.route('/add', methods=['GET', 'POST'])
def add_contact():
    if request.method == 'POST':
        name = request.form['name']
        group = request.form.get('group', '未分组')
        first_letter = get_first_letter(name)

        # ---- 保存头像 ----
        photo_file = request.files.get('photo')
        photo_path = None
        if photo_file and photo_file.filename:
            avatar_dir = os.path.join(app.root_path, 'static', 'avatars')
            os.makedirs(avatar_dir, exist_ok=True)
            photo_path = os.path.join('static', 'avatars', photo_file.filename)
            photo_file.save(os.path.join(app.root_path, photo_path))

        new_contact = Contact(
            name=name,
            group=group,
            first_letter=first_letter,
            photo_path=photo_path
        )
        db.session.add(new_contact)
        db.session.flush()

        methods = request.form.getlist('method_type[]')
        values = request.form.getlist('value[]')
        for mtype, val in zip(methods, values):
            if mtype and val:
                db.session.add(ContactMethod(contact_id=new_contact.id, method_type=mtype, value=val))

        db.session.commit()
        flash(f'联系人 "{name}" 已添加。', 'success')
        return redirect(url_for('index'))

    full_html = BASE_HTML.replace('{% block content %}{% endblock %}', ADD_EDIT_HTML_CONTENT)
    return render_template_string(full_html, contact=None)


@app.route('/edit/<int:contact_id>', methods=['GET', 'POST'])
def edit_contact(contact_id):
    contact = db.get_or_404(Contact, contact_id)

    if request.method == 'POST':
        contact.name = request.form['name']
        contact.group = request.form.get('group', '未分组')
        contact.first_letter = get_first_letter(contact.name)

        # ---- 头像更新 ----
        photo_file = request.files.get('photo')
        if photo_file and photo_file.filename:
            avatar_dir = os.path.join(app.root_path, 'static', 'avatars')
            os.makedirs(avatar_dir, exist_ok=True)
            photo_path = os.path.join('static', 'avatars', photo_file.filename)
            photo_file.save(os.path.join(app.root_path, photo_path))
            contact.photo_path = photo_path

        # ---- 联系方式更新 ----
        ContactMethod.query.filter_by(contact_id=contact.id).delete()
        methods = request.form.getlist('method_type[]')
        values = request.form.getlist('value[]')
        for mtype, val in zip(methods, values):
            if mtype and val:
                db.session.add(ContactMethod(contact_id=contact.id, method_type=mtype, value=val))

        db.session.commit()
        flash(f'联系人 "{contact.name}" 已更新。', 'success')
        return redirect(url_for('index'))

    full_html = BASE_HTML.replace('{% block content %}{% endblock %}', ADD_EDIT_HTML_CONTENT)
    return render_template_string(full_html, contact=contact)


@app.route('/delete/<int:contact_id>', methods=['POST'])
def delete_contact(contact_id):
    contact = db.get_or_404(Contact, contact_id)
    db.session.delete(contact)
    db.session.commit()
    flash(f'联系人 "{contact.name}" 已删除。', 'warning')
    return redirect(url_for('index'))


@app.route('/bookmark/<int:contact_id>', methods=['POST'])
def toggle_bookmark(contact_id):
    contact = db.get_or_404(Contact, contact_id)
    contact.is_bookmarked = not contact.is_bookmarked
    db.session.commit()
    flash(f'联系人 "{contact.name}" 的收藏状态已更新。', 'info')
    return redirect(url_for('index'))


@app.route('/export')
def export_contacts():
    contacts_data = db.session.query(Contact, ContactMethod).outerjoin(ContactMethod).all()

    export_rows = []
    contact_dict = {}

    for contact, method in contacts_data:
        if contact.id not in contact_dict:
            contact_dict[contact.id] = {
                '姓名': contact.name,
                '分组': contact.group,
                '收藏': '是' if contact.is_bookmarked else '否',
                '首字母': contact.first_letter,
                '联系方式': []
            }
        if method:
            contact_dict[contact.id]['联系方式'].append(f"{method.method_type}: {method.value}")

    for cid, info in contact_dict.items():
        export_rows.append({
            '姓名': info['姓名'],
            '分组': info['分组'],
            '收藏': info['收藏'],
            '首字母': info['首字母'],
            '联系方式 (Type: Value)': '; '.join(info['联系方式'])
        })

    df = pd.DataFrame(export_rows)
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="联系人导出.xlsx")


@app.route('/import', methods=['POST'])
def import_contacts():
    if 'file' not in request.files or not request.files['file'].filename:
        flash("未选择文件", "danger")
        return redirect(url_for('index'))

    file = request.files['file']
    df = pd.read_excel(file)

    imported = 0

    for _, row in df.iterrows():
        name = str(row.get('姓名', '')).strip()
        if not name:
            continue

        group = str(row.get('分组', '未分组'))
        is_bookmarked = str(row.get('收藏', '否')) == '是'
        contact_string = str(row.get('联系方式 (Type: Value)', '')).strip()

        contact = Contact.query.filter_by(name=name).first()
        if not contact:
            contact = Contact(name=name)
            db.session.add(contact)
            db.session.flush()

        contact.group = group
        contact.is_bookmarked = is_bookmarked
        contact.first_letter = get_first_letter(name)

        ContactMethod.query.filter_by(contact_id=contact.id).delete()
        for part in contact_string.split(';'):
            if ':' in part:
                t, v = part.split(':', 1)
                db.session.add(ContactMethod(
                    contact_id=contact.id,
                    method_type=t.strip(),
                    value=v.strip()
                ))

        imported += 1

    db.session.commit()
    flash(f"成功导入 {imported} 个联系人", "success")
    return redirect(url_for('index'))


# ==================================
# 4. HTML 模板（美化版）
# ==================================
BASE_HTML = '''
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>联系人地址簿</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --primary: #4361ee;
            --primary-light: #4895ef;
            --secondary: #3f37c9;
            --success: #4cc9f0;
            --info: #7209b7;
            --warning: #f72585;
            --light: #f8f9fa;
            --dark: #212529;
            --gray: #6c757d;
            --border: #dee2e6;
            --shadow: rgba(0, 0, 0, 0.1);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: \'Segoe UI\', \'Helvetica Neue\', Arial, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            color: var(--dark);
            line-height: 1.6;
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 15px 35px var(--shadow);
            overflow: hidden;
            padding: 30px;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 25px;
            margin-bottom: 30px;
            border-bottom: 2px solid var(--border);
        }

        .header h1 {
            color: var(--primary);
            font-size: 2.2rem;
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .header h1 i {
            color: var(--info);
        }

        .flash {
            padding: 15px 20px;
            margin: 20px 0;
            border-radius: 12px;
            border-left: 5px solid;
            font-weight: 500;
            animation: fadeIn 0.5s ease;
        }

        .success {
            background-color: rgba(76, 201, 240, 0.15);
            border-left-color: var(--success);
            color: #0c5460;
        }

        .danger {
            background-color: rgba(247, 37, 133, 0.15);
            border-left-color: var(--warning);
            color: #721c24;
        }

        .info {
            background-color: rgba(114, 9, 183, 0.15);
            border-left-color: var(--info);
            color: #004085;
        }

        .warning {
            background-color: rgba(255, 193, 7, 0.15);
            border-left-color: #ffc107;
            color: #856404;
        }

        .action-bar {
            display: flex;
            gap: 15px;
            margin-bottom: 30px;
            flex-wrap: wrap;
            padding: 20px;
            background: var(--light);
            border-radius: 15px;
        }

        .btn {
            padding: 12px 24px;
            border-radius: 10px;
            border: none;
            cursor: pointer;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: all 0.3s ease;
            text-decoration: none;
            font-size: 0.95rem;
        }

        .btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }

        .btn-primary {
            background: var(--primary);
            color: white;
        }

        .btn-primary:hover {
            background: var(--secondary);
        }

        .btn-success {
            background: var(--success);
            color: white;
        }

        .btn-success:hover {
            background: #0dcaf0;
        }

        .btn-warning {
            background: var(--warning);
            color: white;
        }

        .btn-warning:hover {
            background: #e1156e;
        }

        .btn-danger {
            background: #dc3545;
            color: white;
        }

        .btn-danger:hover {
            background: #bb2d3b;
        }

        .btn-light {
            background: var(--light);
            color: var(--dark);
        }

        .btn-light:hover {
            background: #e9ecef;
        }

        .import-form {
            display: flex;
            gap: 10px;
            align-items: center;
            background: white;
            padding: 10px 15px;
            border-radius: 10px;
            border: 2px dashed var(--border);
        }

        .import-form input[type="file"] {
            padding: 8px;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--light);
        }

        table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            margin-top: 20px;
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.05);
        }

        thead {
            background: linear-gradient(to right, var(--primary), var(--primary-light));
        }

        th {
            padding: 20px 15px;
            text-align: left;
            color: white;
            font-weight: 600;
            border-bottom: 2px solid var(--border);
        }

        td {
            padding: 18px 15px;
            border-bottom: 1px solid var(--border);
            vertical-align: middle;
        }

        tbody tr {
            transition: all 0.2s ease;
        }

        tbody tr:hover {
            background-color: rgba(67, 97, 238, 0.05);
            transform: scale(1.002);
        }

        tbody tr:last-child td {
            border-bottom: none;
        }

        .avatar {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            object-fit: cover;
            border: 3px solid var(--light);
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.1);
            vertical-align: middle;
            margin-right: 15px;
        }

        .contact-name {
            font-weight: 600;
            color: var(--dark);
            font-size: 1.1rem;
        }

        .contact-methods {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .method-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 5px 0;
        }

        .method-type {
            background: var(--primary-light);
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 500;
        }

        .group-badge {
            display: inline-block;
            padding: 6px 15px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 500;
        }

        .group-family { background: #ffeaa7; color: #d63031; }
        .group-colleague { background: #a29bfe; color: #2d3436; }
        .group-friend { background: #81ecec; color: #0984e3; }
        .group-classmate { background: #55efc4; color: #00b894; }
        .group-other { background: #dfe6e9; color: #636e72; }

        .bookmark-btn {
            background: none;
            border: none;
            font-size: 1.8rem;
            cursor: pointer;
            color: #ffd700;
            transition: transform 0.3s ease;
        }

        .bookmark-btn:hover {
            transform: scale(1.2);
        }

        .action-buttons {
            display: flex;
            gap: 10px;
        }

        .action-buttons form {
            display: inline;
        }

        .form-container {
            max-width: 700px;
            margin: 0 auto;
            padding: 30px;
            background: var(--light);
            border-radius: 20px;
        }

        .form-group {
            margin-bottom: 25px;
        }

        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: var(--dark);
            font-size: 1rem;
        }

        .form-control {
            width: 100%;
            padding: 14px 18px;
            border: 2px solid var(--border);
            border-radius: 12px;
            font-size: 1rem;
            transition: all 0.3s ease;
            background: white;
        }

        .form-control:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(67, 97, 238, 0.2);
        }

        select.form-control {
            appearance: none;
            background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e");
            background-repeat: no-repeat;
            background-position: right 15px center;
            background-size: 16px;
            padding-right: 45px;
        }

        .photo-preview {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            object-fit: cover;
            border: 4px solid white;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
            margin-top: 15px;
        }

        .method-container {
            background: white;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 25px;
        }

        .add-method {
            background: var(--success);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            margin-top: 10px;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }

        .footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid var(--border);
            color: var(--gray);
            font-size: 0.9rem;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @media (max-width: 768px) {
            .container {
                padding: 15px;
            }

            .header {
                flex-direction: column;
                align-items: flex-start;
                gap: 15px;
            }

            .action-bar {
                flex-direction: column;
            }

            .import-form {
                flex-direction: column;
                align-items: stretch;
            }

            table {
                display: block;
                overflow-x: auto;
            }

            .action-buttons {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
<div class="container">

{% with messages = get_flashed_messages(with_categories=true) %}
{% for category, msg in messages %}
<div class="flash {{category}}">{{msg}}</div>
{% endfor %}
{% endwith %}

{% block content %}{% endblock %}

</div>
</body>
</html>
'''

INDEX_HTML_CONTENT = '''
<div class="header">
    <h1><i class="fas fa-address-book"></i> 联系人地址簿</h1>
</div>

<div class="action-bar">
    <a href="{{url_for('add_contact')}}" class="btn btn-success">
        <i class="fas fa-user-plus"></i> 新增联系人
    </a>
    <a href="{{url_for('export_contacts')}}" class="btn btn-primary">
        <i class="fas fa-file-export"></i> 导出 Excel
    </a>

    <form method="POST" action="{{url_for('import_contacts')}}" enctype="multipart/form-data" class="import-form">
        <input type="file" name="file" accept=".xlsx" required>
        <button class="btn btn-warning" type="submit">
            <i class="fas fa-file-import"></i> 导入 Excel
        </button>
    </form>
</div>

<table>
<thead>
<tr>
    <th><i class="fas fa-user"></i> 姓名</th>
    <th><i class="fas fa-phone-alt"></i> 联系方式</th>
    <th><i class="fas fa-users"></i> 分组</th>
    <th><i class="fas fa-star"></i> 收藏</th>
    <th><i class="fas fa-cog"></i> 操作</th>
</tr>
</thead>
<tbody>
{% for c in contacts %}
<tr>
    <td>
        <div style="display: flex; align-items: center;">
            {% if c.photo_path %}
                <img src="/{{c.photo_path}}" class="avatar" alt="{{c.name}}的头像">
            {% else %}
                <div class="avatar" style="background: linear-gradient(135deg, var(--primary), var(--info)); 
                    display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                    {{ c.first_letter }}
                </div>
            {% endif %}
            <div>
                <div class="contact-name">{{c.name}}</div>
                <div style="font-size: 0.85rem; color: var(--gray);">首字母: {{c.first_letter}}</div>
            </div>
        </div>
    </td>

    <td>
        <div class="contact-methods">
            {% for m in c.methods.all() %}
                <div class="method-item">
                    <span class="method-type">{{m.method_type}}</span>
                    <span>{{m.value}}</span>
                </div>
            {% endfor %}
        </div>
    </td>

    <td>
        {% if c.group == "家人" %}
            <span class="group-badge group-family"><i class="fas fa-home"></i> {{c.group}}</span>
        {% elif c.group == "同事" %}
            <span class="group-badge group-colleague"><i class="fas fa-briefcase"></i> {{c.group}}</span>
        {% elif c.group == "朋友" %}
            <span class="group-badge group-friend"><i class="fas fa-user-friends"></i> {{c.group}}</span>
        {% elif c.group == "同学" %}
            <span class="group-badge group-classmate"><i class="fas fa-graduation-cap"></i> {{c.group}}</span>
        {% else %}
            <span class="group-badge group-other"><i class="fas fa-tag"></i> {{c.group}}</span>
        {% endif %}
    </td>

    <td>
        <form method="POST" action="{{url_for('toggle_bookmark', contact_id=c.id)}}">
            <button type="submit" class="bookmark-btn">
                {% if c.is_bookmarked %}
                    <i class="fas fa-star"></i>
                {% else %}
                    <i class="far fa-star"></i>
                {% endif %}
            </button>
        </form>
    </td>

    <td>
        <div class="action-buttons">
            <a href="{{url_for('edit_contact', contact_id=c.id)}}" class="btn btn-light">
                <i class="fas fa-edit"></i> 编辑
            </a>
            <form method="POST" action="{{url_for('delete_contact', contact_id=c.id)}}"
                  onsubmit="return confirm(\'确定要删除 {{c.name}} 吗？此操作不可撤销。\');">
                <button type="submit" class="btn btn-danger">
                    <i class="fas fa-trash-alt"></i> 删除
                </button>
            </form>
        </div>
    </td>
</tr>
{% endfor %}
</tbody>
</table>

<div class="footer">
    <p>共 {{ contacts|length }} 个联系人 | 系统版本 2.0 | 美化界面</p>
</div>

<script>
// 添加动态效果
document.addEventListener('DOMContentLoaded', function() {
    // 为表格行添加动画延迟
    const rows = document.querySelectorAll('tbody tr');
    rows.forEach((row, index) => {
        row.style.animationDelay = `${index * 0.05}s`;
        row.style.animation = 'fadeIn 0.5s ease forwards';
    });

    // 确认删除对话框美化
    const deleteForms = document.querySelectorAll('form[onsubmit*="confirm"]');
    deleteForms.forEach(form => {
        const originalSubmit = form.onsubmit;
        form.onsubmit = function(e) {
            e.preventDefault();
            const name = this.querySelector('button').getAttribute('onclick') || this.getAttribute('onsubmit');
            if (confirm('⚠️ 确定要删除联系人吗？\\n\\n此操作将永久删除该联系人的所有信息，无法恢复！')) {
                this.submit();
            }
        };
    });
});
</script>
'''

ADD_EDIT_HTML_CONTENT = '''
<div class="header">
    <h1><i class="fas fa-user-edit"></i> {{ "编辑联系人" if contact else "添加新联系人" }}</h1>
    <a href="{{url_for('index')}}" class="btn btn-light">
        <i class="fas fa-arrow-left"></i> 返回列表
    </a>
</div>

<div class="form-container">
    <form method="POST" enctype="multipart/form-data">
        <div class="form-group">
            <label for="name"><i class="fas fa-signature"></i> 姓名 *</label>
            <input type="text" id="name" name="name" class="form-control" required 
                   value="{{contact.name if contact else ""}}" 
                   placeholder="请输入联系人姓名">
        </div>

        <div class="form-group">
            <label for="group"><i class="fas fa-users"></i> 分组</label>
            <select id="group" name="group" class="form-control">
                {% set g = contact.group if contact else "未分组" %}
                <option value="家人" {% if g=="家人" %}selected{% endif %}>👨‍👩‍👧‍👦 家人</option>
                <option value="同事" {% if g=="同事" %}selected{% endif %}>💼 同事</option>
                <option value="朋友" {% if g=="朋友" %}selected{% endif %}>👫 朋友</option>
                <option value="同学" {% if g=="同学" %}selected{% endif %}>🎓 同学</option>
                <option value="未分组" {% if g=="未分组" %}selected{% endif %}>🏷️ 未分组</option>
            </select>
        </div>

        <div class="form-group">
            <label for="photo"><i class="fas fa-camera"></i> 头像</label>
            <input type="file" id="photo" name="photo" class="form-control" accept="image/*">
            {% if contact and contact.photo_path %}
                <div style="text-align: center; margin-top: 15px;">
                    <p>当前头像：</p>
                    <img src="/{{contact.photo_path}}" class="photo-preview" alt="当前头像">
                </div>
            {% endif %}
        </div>

        <div class="method-container">
            <h3 style="margin-bottom: 20px; color: var(--primary);">
                <i class="fas fa-address-card"></i> 联系方式
            </h3>

            <div id="contact-methods">
                {% set lst = contact.methods.all() if contact else [] %}
                {% if lst %}
                    {% for m in lst %}
                        <div class="form-group method-row" style="display: flex; gap: 10px; margin-bottom: 15px;">
                            <select name="method_type[]" class="form-control" style="flex: 1;">
                                <option value="电话" {% if m.method_type=="电话" %}selected{% endif %}>📞 电话</option>
                                <option value="邮箱" {% if m.method_type=="邮箱" %}selected{% endif %}>✉️ 邮箱</option>
                                <option value="微信" {% if m.method_type=="微信" %}selected{% endif %}>💬 微信</option>
                                <option value="QQ" {% if m.method_type=="QQ" %}selected{% endif %}>💻 QQ</option>
                                <option value="地址" {% if m.method_type=="地址" %}selected{% endif %}>🏠 地址</option>
                            </select>
                            <input type="text" name="value[]" class="form-control" style="flex: 2;" 
                                   value="{{m.value}}" placeholder="输入联系方式">
                            <button type="button" class="btn btn-danger remove-method" style="flex: 0 0 auto;">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    {% endfor %}
                {% else %}
                    <div class="form-group method-row" style="display: flex; gap: 10px; margin-bottom: 15px;">
                        <select name="method_type[]" class="form-control" style="flex: 1;">
                            <option value="电话">📞 电话</option>
                            <option value="邮箱">✉️ 邮箱</option>
                            <option value="微信">💬 微信</option>
                            <option value="QQ">💻 QQ</option>
                            <option value="地址">🏠 地址</option>
                        </select>
                        <input type="text" name="value[]" class="form-control" style="flex: 2;" 
                               placeholder="输入联系方式">
                        <button type="button" class="btn btn-danger remove-method" style="flex: 0 0 auto;">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                {% endif %}
            </div>

            <button type="button" id="add-method" class="add-method">
                <i class="fas fa-plus"></i> 添加联系方式
            </button>
        </div>

        <div style="display: flex; gap: 15px; margin-top: 30px;">
            <button type="submit" class="btn btn-success" style="flex: 1; padding: 15px;">
                <i class="fas fa-save"></i> {{"保存更改" if contact else "添加联系人"}}
            </button>
            <a href="{{url_for('index')}}" class="btn btn-danger" style="flex: 1; padding: 15px; text-align: center;">
                <i class="fas fa-times"></i> 取消
            </a>
        </div>
    </form>
</div>

<script>
document.addEventListener("DOMContentLoaded", function() {
    // 添加联系方式行
    document.getElementById("add-method").addEventListener("click", function() {
        const methodsDiv = document.getElementById("contact-methods");
        const newRow = document.createElement("div");
        newRow.className = "form-group method-row";
        newRow.style.cssText = "display: flex; gap: 10px; margin-bottom: 15px;";
        newRow.innerHTML = `
            <select name="method_type[]" class="form-control" style="flex: 1;">
                <option value="电话">📞 电话</option>
                <option value="邮箱">✉️ 邮箱</option>
                <option value="微信">💬 微信</option>
                <option value="QQ">💻 QQ</option>
                <option value="地址">🏠 地址</option>
            </select>
            <input type="text" name="value[]" class="form-control" style="flex: 2;" placeholder="输入联系方式">
            <button type="button" class="btn btn-danger remove-method" style="flex: 0 0 auto;">
                <i class="fas fa-times"></i>
            </button>
        `;
        methodsDiv.appendChild(newRow);

        // 为新行的删除按钮添加事件
        newRow.querySelector(".remove-method").addEventListener("click", function() {
            if (methodsDiv.children.length > 1) {
                this.parentElement.remove();
            }
        });
    });

    // 为现有删除按钮添加事件
    document.querySelectorAll(".remove-method").forEach(btn => {
        btn.addEventListener("click", function() {
            const methodsDiv = document.getElementById("contact-methods");
            if (methodsDiv.children.length > 1) {
                this.parentElement.remove();
            }
        });
    });

    // 头像预览功能
    document.getElementById("photo").addEventListener("change", function(e) {
        if (this.files && this.files[0]) {
            const reader = new FileReader();
            reader.onload = function(e) {
                const preview = document.querySelector(".photo-preview");
                if (preview) {
                    preview.src = e.target.result;
                } else {
                    const container = document.getElementById("photo").parentElement;
                    const previewImg = document.createElement("img");
                    previewImg.className = "photo-preview";
                    previewImg.src = e.target.result;
                    previewImg.alt = "头像预览";
                    container.appendChild(previewImg);
                }
            };
            reader.readAsDataURL(this.files[0]);
        }
    });
});
</script>
'''

# ==================================
# 5. 应用启动
# ==================================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("系统已启动，增强功能已启用：分组 / 头像 / 首字母排序 ✔")
        print("美化界面已加载，访问 http://127.0.0.1:5000")
    app.run(debug=True)