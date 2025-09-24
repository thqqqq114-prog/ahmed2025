import unittest
from datetime import datetime, timedelta
from app.data.database import get_item_stock, is_date_locked, log_action
from app.data.models import Base, Supplier, Item, Delivery, Invoice, InvoiceLine
from sqlalchemy import text
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class TestDatabaseFunctions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # إنشاء قاعدة بيانات في الذاكرة للاختبار
        cls.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)
        
        # إعداد بيانات اختبارية
        with cls.Session() as session:
            # إضافة مورد
            supplier = Supplier(name="مورد اختبار")
            session.add(supplier)
            session.commit()
            
            # إضافة أصناف
            item1 = Item(name="تفاح", min_stock=50)
            item2 = Item(name="برتقال", min_stock=30)
            session.add_all([item1, item2])
            session.commit()
            
            # إضافة توريدات
            delivery1 = Delivery(
                supplier_id=supplier.id,
                item_id=item1.id,
                quantity=100,
                unit="kg",
                price_per_unit=5,
                total_price=500
            )
            delivery2 = Delivery(
                supplier_id=supplier.id,
                item_id=item2.id,
                quantity=200,
                unit="kg",
                price_per_unit=3,
                total_price=600
            )
            session.add_all([delivery1, delivery2])
            
            # إضافة فاتورة وخط فاتورة للتفاح فقط
            invoice = Invoice(
                supplier_id=supplier.id,
                customer_name="عميل اختبار",
                total_amount=150,
                discount_amount=0,
                tax_amount=0,
                net_amount=150,
                status='posted',
                created_at=datetime.now()
            )
            session.add(invoice)
            session.flush()  # للحصول على معرف الفاتورة
            
            invoice_line1 = InvoiceLine(
                invoice_id=invoice.id,
                item_id=item1.id,
                quantity=30,
                unit='kg',
                unit_price=5,
                discount=0,
                line_total=150
            )
            session.add(invoice_line1)
            session.commit()

    def test_get_item_stock(self):
        """اختبار حساب رصيد الأصناف"""
        with self.engine.connect() as conn:
            with self.Session() as session:
                apple = session.query(Item).filter_by(name="تفاح").first()
                orange = session.query(Item).filter_by(name="برتقال").first()
                # 100 (توريد) - 30 (فاتورة) = 70
                self.assertEqual(get_item_stock(apple.id, conn=conn), 70.0)
                # اختبار صنف البرتقال: 200 (توريد) - 0 (سحب) = 200
                self.assertEqual(get_item_stock(orange.id, conn=conn), 200.0)
                # 200 (توريد) - 0 (فواتير) = 200
                self.assertEqual(get_item_stock(orange.id, conn=conn), 200.0)

    def test_is_date_locked(self):
        """اختبار التحقق من قفل الفترة"""
        test_date = datetime.now().date()
        lock_from = (test_date - timedelta(days=5)).strftime("%Y-%m-%d")
        lock_to = (test_date + timedelta(days=5)).strftime("%Y-%m-%d")
        with self.engine.connect() as conn:
            with self.Session() as session:
                session.execute(text("INSERT INTO app_settings (key, value) VALUES ('lock_from', :val)"), {"val": lock_from})
                session.execute(text("INSERT INTO app_settings (key, value) VALUES ('lock_to', :val)"), {"val": lock_to})
                session.commit()
                # تاريخ قبل القفل
                self.assertTrue(is_date_locked(datetime.now() - timedelta(days=10), conn=conn))
                # تاريخ بعد القفل
                self.assertTrue(is_date_locked(datetime.now() + timedelta(days=10), conn=conn))
                # تاريخ داخل الفترة المسموحة
                self.assertFalse(is_date_locked(datetime.now(), conn=conn))

    def test_log_action(self):
        """اختبار تسجيل حركات المراجعة"""
        with self.engine.connect() as conn:
            # تسجيل حركة
            log_action("test_user", "create", "item", 1, "test details", conn=conn)
            # التحقق من تسجيل الحركة
            result = conn.execute(text("SELECT * FROM audit_logs")).fetchone()
            self.assertIsNotNone(result)
            self.assertEqual(result.username, "test_user")
            self.assertEqual(result.action, "create")
            self.assertEqual(result.entity, "item")

if __name__ == "__main__":
    unittest.main()