#!/bin/bash

# 🚀 سكريپت إعداد خادم التراخيص الشامل
# يقوم بإعداد السيرفر من الصفر مع ربط الدومين

set -e  # إيقاف السكريپت عند أي خطأ

# الألوان للعرض
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# دالة لطباعة الرسائل الملونة
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# التحقق من تشغيل السكريپت كـ root
if [[ $EUID -ne 0 ]]; then
   print_error "يجب تشغيل هذا السكريپت كـ root"
   exit 1
fi

print_header "🚀 بدء إعداد خادم التراخيص"

# طلب المعلومات من المستخدم
read -p "أدخل اسم النطاق (مثال: ahmedhussein.online): " DOMAIN
read -p "أدخل البريد الإلكتروني للـ SSL: " EMAIL
read -s -p "أدخل كلمة مرور قاعدة البيانات: " DB_PASSWORD
echo
read -s -p "أدخل كلمة مرور المدير: " ADMIN_PASSWORD
echo

# التحقق من صحة المدخلات
if [[ -z "$DOMAIN" || -z "$EMAIL" || -z "$DB_PASSWORD" || -z "$ADMIN_PASSWORD" ]]; then
    print_error "جميع الحقول مطلوبة!"
    exit 1
fi

print_status "النطاق: $DOMAIN"
print_status "البريد الإلكتروني: $EMAIL"

# الخطوة 1: تحديث النظام
print_header "📦 تحديث النظام"
apt update && apt upgrade -y

# الخطوة 2: تثبيت الحزم الأساسية
print_header "🔧 تثبيت الحزم الأساسية"
apt install -y curl wget unzip software-properties-common apt-transport-https ca-certificates gnupg lsb-release

# الخطوة 3: تثبيت Nginx
print_header "🌐 تثبيت Nginx"
apt install -y nginx
systemctl enable nginx
systemctl start nginx

# الخطوة 4: تثبيت PHP 8.1
print_header "🐘 تثبيت PHP 8.1"
add-apt-repository ppa:ondrej/php -y
apt update
apt install -y php8.1-fpm php8.1-mysql php8.1-curl php8.1-json php8.1-mbstring php8.1-xml php8.1-zip php8.1-gd php8.1-intl php8.1-bcmath

# الخطوة 5: تثبيت MySQL
print_header "🗄️ تثبيت MySQL"
apt install -y mysql-server

# تأمين MySQL
mysql_secure_installation <<EOF

y
$DB_PASSWORD
$DB_PASSWORD
y
y
y
y
EOF

# الخطوة 6: إعداد قاعدة البيانات
print_header "🗃️ إعداد قاعدة البيانات"
mysql -u root -p$DB_PASSWORD <<EOF
CREATE DATABASE farmapp_licenses CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'farmapp_user'@'localhost' IDENTIFIED BY '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON farmapp_licenses.* TO 'farmapp_user'@'localhost';
FLUSH PRIVILEGES;
EOF

print_status "تم إنشاء قاعدة البيانات: farmapp_licenses"

# الخطوة 7: إعداد مجلدات الموقع
print_header "📁 إعداد مجلدات الموقع"
mkdir -p /var/www/$DOMAIN
mkdir -p /var/www/$DOMAIN/uploads
mkdir -p /var/www/$DOMAIN/logs
mkdir -p /var/www/$DOMAIN/backups
mkdir -p /var/www/$DOMAIN/api
mkdir -p /var/www/$DOMAIN/admin

# الخطوة 8: إنشاء ملفات الموقع
print_header "📄 إنشاء ملفات الموقع"

# إنشاء ملف التكوين
cat > /var/www/$DOMAIN/config.php << EOF
<?php
// إعدادات قاعدة البيانات
define('DB_HOST', 'localhost');
define('DB_NAME', 'farmapp_licenses');
define('DB_USER', 'farmapp_user');
define('DB_PASS', '$DB_PASSWORD');

// إعدادات الموقع
define('SITE_URL', 'https://$DOMAIN');
define('ADMIN_EMAIL', '$EMAIL');
define('SECRET_KEY', '$(openssl rand -hex 32)');

// مسارات الملفات
define('UPLOAD_PATH', '/var/www/$DOMAIN/uploads/');
define('LOG_PATH', '/var/www/$DOMAIN/logs/');

// إعدادات الأمان
define('FORCE_SSL', true);
define('PRODUCTION_MODE', true);
define('DEBUG_MODE', false);

// معلومات التطبيق
define('APP_NAME', 'FarmApp License Server');
define('APP_VERSION', '1.0.0');
define('TIMEZONE', 'Africa/Cairo');

date_default_timezone_set(TIMEZONE);
?>
EOF

# إنشاء الصفحة الرئيسية
cat > /var/www/$DOMAIN/index.php << 'EOF'
<?php
include_once 'config.php';
?>
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo APP_NAME; ?></title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            text-align: center;
            max-width: 600px;
            width: 90%;
        }
        h1 { color: #333; margin-bottom: 20px; font-size: 2.5em; }
        .status { padding: 15px; border-radius: 8px; margin: 20px 0; font-weight: bold; }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .btn {
            display: inline-block;
            padding: 12px 25px;
            margin: 10px;
            background: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: bold;
            transition: all 0.3s;
        }
        .btn:hover { background: #0056b3; transform: translateY(-2px); }
        .info {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            text-align: right;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 <?php echo APP_NAME; ?></h1>
        <div class="status success">✅ الخادم يعمل بنجاح!</div>
        
        <div style="margin: 30px 0;">
            <a href="admin/" class="btn">لوحة الإدارة</a>
            <a href="api/test.php" class="btn">اختبار API</a>
        </div>
        
        <div class="info">
            <h3>معلومات الخادم:</h3>
            <p><strong>النطاق:</strong> <?php echo SITE_URL; ?></p>
            <p><strong>الإصدار:</strong> <?php echo APP_VERSION; ?></p>
            <p><strong>حالة SSL:</strong> <?php echo FORCE_SSL ? 'مفعل' : 'غير مفعل'; ?></p>
        </div>
    </div>
</body>
</html>
EOF

# إنشاء API للتحقق من التراخيص
cat > /var/www/$DOMAIN/api/license_check.php << 'EOF'
<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

include_once '../config.php';

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

try {
    $conn = new mysqli(DB_HOST, DB_USER, DB_PASS, DB_NAME);
    
    if ($conn->connect_error) {
        throw new Exception('Database connection failed');
    }
    
    $input = json_decode(file_get_contents('php://input'), true);
    $license_key = $input['license_key'] ?? $_POST['license_key'] ?? '';
    $device_id = $input['device_id'] ?? $_POST['device_id'] ?? '';
    
    if (empty($license_key)) {
        echo json_encode(['valid' => false, 'message' => 'License key required']);
        exit;
    }
    
    $stmt = $conn->prepare("SELECT * FROM licenses WHERE license_key = ? AND status = 'active'");
    $stmt->bind_param("s", $license_key);
    $stmt->execute();
    $result = $stmt->get_result();
    $license = $result->fetch_assoc();
    
    if ($license) {
        // تحديث معرف الجهاز إذا لم يكن موجود
        if (empty($license['device_id']) && !empty($device_id)) {
            $update_stmt = $conn->prepare("UPDATE licenses SET device_id = ? WHERE id = ?");
            $update_stmt->bind_param("si", $device_id, $license['id']);
            $update_stmt->execute();
        }
        
        echo json_encode([
            'valid' => true,
            'status' => 'active',
            'message' => 'License is valid',
            'expires_at' => $license['expires_at']
        ]);
    } else {
        echo json_encode([
            'valid' => false,
            'status' => 'invalid',
            'message' => 'License not found or inactive'
        ]);
    }
    
    $conn->close();
    
} catch (Exception $e) {
    echo json_encode(['valid' => false, 'message' => 'Server error']);
}
?>
EOF

# إنشاء API للتحقق من التحديثات
cat > /var/www/$DOMAIN/api/update_check.php << 'EOF'
<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$current_version = $_GET['version'] ?? '1.0.0';
$latest_version = '1.0.0';

echo json_encode([
    'update_available' => version_compare($current_version, $latest_version, '<'),
    'latest_version' => $latest_version,
    'current_version' => $current_version,
    'download_url' => SITE_URL . '/downloads/latest.zip',
    'message' => version_compare($current_version, $latest_version, '<') 
        ? 'تحديث متاح' 
        : 'لديك أحدث إصدار'
]);
?>
EOF

# إنشاء ملف اختبار API
cat > /var/www/$DOMAIN/api/test.php << 'EOF'
<?php
include_once '../config.php';
?>
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <title>اختبار API</title>
    <style>
        body { font-family: Arial; margin: 20px; }
        .test { background: #f0f0f0; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .success { color: green; }
        .error { color: red; }
    </style>
</head>
<body>
    <h1>🧪 اختبار API</h1>
    
    <div class="test">
        <h3>اختبار فحص التحديثات:</h3>
        <p><a href="update_check.php?version=1.0.0" target="_blank">GET update_check.php?version=1.0.0</a></p>
    </div>
    
    <div class="test">
        <h3>اختبار فحص الترخيص:</h3>
        <form method="post" action="license_check.php" target="_blank">
            <p>مفتاح الترخيص: <input type="text" name="license_key" value="test-license" required></p>
            <p>معرف الجهاز: <input type="text" name="device_id" value="test-device"></p>
            <p><button type="submit">اختبار</button></p>
        </form>
    </div>
    
    <p><a href="../">العودة للصفحة الرئيسية</a></p>
</body>
</html>
EOF

# إنشاء لوحة الإدارة البسيطة
cat > /var/www/$DOMAIN/admin/index.php << 'EOF'
<?php
session_start();
include_once '../config.php';

// تسجيل الدخول
if ($_POST && isset($_POST['login'])) {
    $username = $_POST['username'];
    $password = $_POST['password'];
    
    $conn = new mysqli(DB_HOST, DB_USER, DB_PASS, DB_NAME);
    $stmt = $conn->prepare("SELECT * FROM users WHERE username = ?");
    $stmt->bind_param("s", $username);
    $stmt->execute();
    $result = $stmt->get_result();
    $user = $result->fetch_assoc();
    
    if ($user && password_verify($password, $user['password'])) {
        $_SESSION['user_id'] = $user['id'];
        $_SESSION['username'] = $user['username'];
        header('Location: index.php');
        exit;
    } else {
        $error = 'اسم المستخدم أو كلمة المرور خاطئة';
    }
}

// إضافة ترخيص
if ($_POST && isset($_POST['add_license']) && isset($_SESSION['user_id'])) {
    $license_key = $_POST['license_key'];
    $device_id = $_POST['device_id'] ?? '';
    
    $conn = new mysqli(DB_HOST, DB_USER, DB_PASS, DB_NAME);
    $stmt = $conn->prepare("INSERT INTO licenses (license_key, device_id) VALUES (?, ?)");
    $stmt->bind_param("ss", $license_key, $device_id);
    
    if ($stmt->execute()) {
        $success = 'تم إضافة الترخيص بنجاح';
    } else {
        $error = 'خطأ في إضافة الترخيص';
    }
}
?>
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <title>لوحة الإدارة - <?php echo APP_NAME; ?></title>
    <style>
        body { font-family: Arial; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: right; }
        th { background: #f8f9fa; }
        .success { color: green; background: #d4edda; padding: 10px; border-radius: 5px; }
        .error { color: red; background: #f8d7da; padding: 10px; border-radius: 5px; }
        .btn { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
        .form-group { margin: 15px 0; }
        input[type="text"], input[type="password"] { padding: 8px; width: 300px; border: 1px solid #ddd; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <?php if (!isset($_SESSION['user_id'])): ?>
            <h1>تسجيل الدخول</h1>
            <?php if (isset($error)): ?>
                <div class="error"><?php echo $error; ?></div>
            <?php endif; ?>
            <form method="post">
                <div class="form-group">
                    <label>اسم المستخدم:</label><br>
                    <input type="text" name="username" required>
                </div>
                <div class="form-group">
                    <label>كلمة المرور:</label><br>
                    <input type="password" name="password" required>
                </div>
                <button type="submit" name="login" class="btn">دخول</button>
            </form>
        <?php else: ?>
            <h1>لوحة إدارة التراخيص</h1>
            <p>مرحباً <?php echo $_SESSION['username']; ?> | <a href="logout.php">خروج</a> | <a href="../">الموقع الرئيسي</a></p>
            
            <?php if (isset($success)): ?>
                <div class="success"><?php echo $success; ?></div>
            <?php endif; ?>
            <?php if (isset($error)): ?>
                <div class="error"><?php echo $error; ?></div>
            <?php endif; ?>
            
            <h2>إضافة ترخيص جديد</h2>
            <form method="post">
                <div class="form-group">
                    <label>مفتاح الترخيص:</label><br>
                    <input type="text" name="license_key" required>
                </div>
                <div class="form-group">
                    <label>معرف الجهاز (اختياري):</label><br>
                    <input type="text" name="device_id">
                </div>
                <button type="submit" name="add_license" class="btn">إضافة ترخيص</button>
            </form>
            
            <h2>التراخيص الموجودة</h2>
            <?php
            $conn = new mysqli(DB_HOST, DB_USER, DB_PASS, DB_NAME);
            $result = $conn->query("SELECT * FROM licenses ORDER BY created_at DESC LIMIT 50");
            ?>
            <table>
                <tr>
                    <th>المفتاح</th>
                    <th>معرف الجهاز</th>
                    <th>الحالة</th>
                    <th>تاريخ الإنشاء</th>
                </tr>
                <?php while ($row = $result->fetch_assoc()): ?>
                <tr>
                    <td><?php echo htmlspecialchars($row['license_key']); ?></td>
                    <td><?php echo htmlspecialchars($row['device_id']); ?></td>
                    <td><?php echo $row['status']; ?></td>
                    <td><?php echo $row['created_at']; ?></td>
                </tr>
                <?php endwhile; ?>
            </table>
        <?php endif; ?>
    </div>
</body>
</html>
EOF

# إنشاء ملف تسجيل الخروج
cat > /var/www/$DOMAIN/admin/logout.php << 'EOF'
<?php
session_start();
session_destroy();
header('Location: index.php');
exit;
?>
EOF

# إنشاء جداول قاعدة البيانات
cat > /tmp/database_schema.sql << 'EOF'
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    role ENUM('admin', 'user') DEFAULT 'admin',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS licenses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    license_key VARCHAR(255) UNIQUE NOT NULL,
    device_id VARCHAR(255),
    status ENUM('active', 'inactive', 'expired') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    INDEX idx_license_key (license_key),
    INDEX idx_device_id (device_id),
    INDEX idx_status (status)
);

CREATE TABLE IF NOT EXISTS download_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    license_key VARCHAR(255),
    device_id VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    download_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_name VARCHAR(255),
    file_size BIGINT,
    INDEX idx_license_key (license_key),
    INDEX idx_download_time (download_time)
);

CREATE TABLE IF NOT EXISTS system_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    level ENUM('info', 'warning', 'error', 'debug') DEFAULT 'info',
    message TEXT NOT NULL,
    context JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_level (level),
    INDEX idx_created_at (created_at)
);
EOF

# تطبيق قاعدة البيانات
mysql -u root -p$DB_PASSWORD farmapp_licenses < /tmp/database_schema.sql

# إنشاء المستخدم الإداري
HASHED_PASSWORD=$(php -r "echo password_hash('$ADMIN_PASSWORD', PASSWORD_DEFAULT);")
mysql -u root -p$DB_PASSWORD farmapp_licenses -e "INSERT IGNORE INTO users (username, email, password, role) VALUES ('admin', '$EMAIL', '$HASHED_PASSWORD', 'admin');"

# إضافة ترخيص تجريبي
mysql -u root -p$DB_PASSWORD farmapp_licenses -e "INSERT IGNORE INTO licenses (license_key, device_id, status) VALUES ('test-license-123', 'test-device', 'active');"

print_status "تم إنشاء المستخدم الإداري: admin"
print_status "تم إضافة ترخيص تجريبي: test-license-123"

# الخطوة 9: إعداد صلاحيات الملفات
print_header "🔒 إعداد صلاحيات الملفات"
chown -R www-data:www-data /var/www/$DOMAIN
chmod -R 755 /var/www/$DOMAIN
chmod -R 777 /var/www/$DOMAIN/uploads
chmod -R 777 /var/www/$DOMAIN/logs
chmod -R 777 /var/www/$DOMAIN/backups
chmod 600 /var/www/$DOMAIN/config.php

# الخطوة 10: إعداد Nginx
print_header "⚙️ إعداد Nginx"
cat > /etc/nginx/sites-available/$DOMAIN << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    root /var/www/$DOMAIN;
    index index.php index.html index.htm;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied expired no-cache no-store private must-revalidate auth;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/javascript;

    location / {
        try_files \$uri \$uri/ /index.php?\$query_string;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php8.1-fpm.sock;
        fastcgi_param SCRIPT_FILENAME \$document_root\$fastcgi_script_name;
        include fastcgi_params;
        
        # Security
        fastcgi_hide_header X-Powered-By;
        fastcgi_read_timeout 300;
    }

    # Deny access to sensitive files
    location ~ /\.(htaccess|htpasswd|env|git) {
        deny all;
    }

    location ~ /config\.php$ {
        deny all;
    }

    location ~ /\.sql$ {
        deny all;
    }

    # API rate limiting
    location /api/ {
        limit_req zone=api burst=10 nodelay;
        try_files \$uri \$uri/ /index.php?\$query_string;
    }

    # File upload limits
    client_max_body_size 100M;
    client_body_timeout 120s;

    # Logging
    access_log /var/log/nginx/$DOMAIN.access.log;
    error_log /var/log/nginx/$DOMAIN.error.log;
}
EOF

# إعداد rate limiting
cat >> /etc/nginx/nginx.conf << 'EOF'

# Rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=30r/m;
limit_req_zone $binary_remote_addr zone=general:10m rate=60r/m;
EOF

# تفعيل الموقع
ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# اختبار إعدادات Nginx
nginx -t
if [ $? -eq 0 ]; then
    print_status "إعدادات Nginx صحيحة"
    systemctl reload nginx
else
    print_error "خطأ في إعدادات Nginx"
    exit 1
fi

# الخطوة 11: تثبيت SSL مع Let's Encrypt
print_header "🔐 تثبيت شهادة SSL"
apt install -y certbot python3-certbot-nginx

# التأكد من أن النطاق يشير للخادم
print_warning "تأكد من أن النطاق $DOMAIN يشير لعنوان IP هذا الخادم"
print_status "عنوان IP الحالي: $(curl -s ifconfig.me)"
read -p "اضغط Enter للمتابعة بعد التأكد من إعدادات DNS..."

# الحصول على شهادة SSL
certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --email $EMAIL

if [ $? -eq 0 ]; then
    print_status "تم تثبيت شهادة SSL بنجاح"
else
    print_warning "فشل في تثبيت SSL، تحقق من إعدادات DNS"
fi

# الخطوة 12: إعداد جدولة المهام
print_header "⏰ إعداد جدولة المهام"
(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet") | crontab -
(crontab -l 2>/dev/null; echo "0 2 * * 0 mysqldump -u farmapp_user -p$DB_PASSWORD farmapp_licenses > /var/www/$DOMAIN/backups/backup_\$(date +\%Y\%m\%d).sql") | crontab -

# الخطوة 13: إعداد الجدار الناري
print_header "🛡️ إعداد الجدار الناري"
ufw --force enable
ufw allow ssh
ufw allow 'Nginx Full'
ufw allow 80
ufw allow 443

# الخطوة 14: تحسين الأداء
print_header "⚡ تحسين الأداء"

# تحسين PHP
sed -i 's/memory_limit = .*/memory_limit = 256M/' /etc/php/8.1/fpm/php.ini
sed -i 's/upload_max_filesize = .*/upload_max_filesize = 100M/' /etc/php/8.1/fpm/php.ini
sed -i 's/post_max_size = .*/post_max_size = 100M/' /etc/php/8.1/fpm/php.ini
sed -i 's/max_execution_time = .*/max_execution_time = 300/' /etc/php/8.1/fpm/php.ini

# تحسين MySQL
cat >> /etc/mysql/mysql.conf.d/mysqld.cnf << 'EOF'

# Performance tuning
innodb_buffer_pool_size = 256M
innodb_log_file_size = 64M
innodb_flush_log_at_trx_commit = 2
innodb_flush_method = O_DIRECT
query_cache_type = 1
query_cache_size = 32M
EOF

# إعادة تشغيل الخدمات
systemctl restart php8.1-fpm
systemctl restart mysql
systemctl restart nginx

# الخطوة 15: إنشاء ملف معلومات النشر
print_header "📋 إنشاء ملف معلومات النشر"
cat > /var/www/$DOMAIN/deployment_info.txt << EOF
=================================
معلومات نشر خادم التراخيص
=================================

النطاق: https://$DOMAIN
تاريخ النشر: $(date)
إصدار PHP: $(php -v | head -n1)
إصدار MySQL: $(mysql --version)
إصدار Nginx: $(nginx -v 2>&1)

=================================
معلومات قاعدة البيانات
=================================
اسم قاعدة البيانات: farmapp_licenses
اسم المستخدم: farmapp_user
كلمة المرور: [محفوظة في config.php]

=================================
معلومات المدير
=================================
اسم المستخدم: admin
كلمة المرور: [التي أدخلتها أثناء التثبيت]
رابط لوحة الإدارة: https://$DOMAIN/admin/

=================================
روابط مهمة
=================================
الموقع الرئيسي: https://$DOMAIN
لوحة الإدارة: https://$DOMAIN/admin/
اختبار API: https://$DOMAIN/api/test.php
فحص التراخيص: https://$DOMAIN/api/license_check.php
فحص التحديثات: https://$DOMAIN/api/update_check.php

=================================
ملفات السجل
=================================
Nginx Access: /var/log/nginx/$DOMAIN.access.log
Nginx Error: /var/log/nginx/$DOMAIN.error.log
PHP Error: /var/log/php8.1-fpm.log
MySQL Error: /var/log/mysql/error.log

=================================
مجلدات مهمة
=================================
الموقع: /var/www/$DOMAIN
الرفع: /var/www/$DOMAIN/uploads
السجلات: /var/www/$DOMAIN/logs
النسخ الاحتياطية: /var/www/$DOMAIN/backups

=================================
اختبار سريع
=================================
curl -I https://$DOMAIN
curl -X POST https://$DOMAIN/api/license_check.php -H "Content-Type: application/json" -d '{"license_key":"test-license-123","device_id":"test"}'

=================================
EOF

# تنظيف الملفات المؤقتة
rm -f /tmp/database_schema.sql

print_header "🎉 اكتمل الإعداد بنجاح!"
print_status "الموقع: https://$DOMAIN"
print_status "لوحة الإدارة: https://$DOMAIN/admin/"
print_status "اسم المستخدم: admin"
print_status "كلمة المرور: [التي أدخلتها]"
print_status "ترخيص تجريبي: test-license-123"

print_warning "احفظ هذه المعلومات في مكان آمن!"
print_status "ملف المعلومات الكامل: /var/www/$DOMAIN/deployment_info.txt"

echo
print_header "🧪 اختبار سريع"
echo "جاري اختبار الموقع..."
sleep 5

if curl -s -I https://$DOMAIN | grep -q "200 OK"; then
    print_status "✅ الموقع يعمل بنجاح!"
else
    print_warning "⚠️ قد تحتاج لانتظار انتشار DNS"
fi

print_header "✅ تم الانتهاء من جميع الخطوات!"