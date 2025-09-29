#!/bin/bash

# 🚀 سكريپت الإعداد السريع لخادم التراخيص
# للاستخدام: curl -sSL https://raw.githubusercontent.com/yourusername/yourrepo/main/quick_setup.sh | bash

echo "🚀 مرحباً بك في معالج إعداد خادم التراخيص"
echo "=================================="

# التحقق من تشغيل السكريپت كـ root
if [[ $EUID -ne 0 ]]; then
   echo "❌ يجب تشغيل هذا السكريپت كـ root"
   echo "استخدم: sudo bash quick_setup.sh"
   exit 1
fi

# تحديث النظام أولاً
echo "📦 تحديث النظام..."
apt update -y

# تحميل السكريپت الرئيسي
echo "📥 تحميل سكريپت الإعداد الرئيسي..."
wget -O server_setup.sh https://raw.githubusercontent.com/yourusername/yourrepo/main/server_setup.sh

if [ ! -f "server_setup.sh" ]; then
    echo "❌ فشل في تحميل السكريپت"
    echo "يرجى تحميله يدوياً من:"
    echo "https://raw.githubusercontent.com/yourusername/yourrepo/main/server_setup.sh"
    exit 1
fi

# إعطاء صلاحية التنفيذ
chmod +x server_setup.sh

echo "✅ تم تحميل السكريپت بنجاح!"
echo ""
echo "🎯 الآن شغل السكريپت الرئيسي:"
echo "./server_setup.sh"
echo ""
echo "أو للتشغيل المباشر:"
echo "bash server_setup.sh"