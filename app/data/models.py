from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# =============================
# Security / Users
# =============================
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(512), nullable=False)
    salt = Column(String(128), nullable=True)
    is_admin = Column(Boolean, nullable=False, default=True)
    role = Column(String(100), nullable=True)  # admin/editor/viewer
    phone = Column(String(50), nullable=True)
    company = Column(String(500), nullable=True)
    login_attempts = Column(Integer, nullable=False, default=0)
    last_attempt = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

# =============================
# Core Entities
# =============================
class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True)
    name = Column(String(500), nullable=False, unique=True)
    phone = Column(String(50), nullable=True)
    address = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    deliveries = relationship("Delivery", back_populates="supplier", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="supplier", cascade="all, delete-orphan")

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String(500), nullable=False, unique=True)
    default_unit = Column(String(50), nullable=False, default="kg")  # kg, ton, bag, ...
    default_unit_weight = Column(Float, nullable=True)  # e.g., bag=50kg; can be overridden per delivery
    default_price_per_unit = Column(Float, nullable=True)
    allow_price_override = Column(Boolean, nullable=False, default=True)
    min_stock = Column(Float, nullable=True)  # حد أدنى للمخزون (اختياري)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    deliveries = relationship("Delivery", back_populates="item")

class Factory(Base):
    __tablename__ = "factories"
    id = Column(Integer, primary_key=True)
    name = Column(String(500), nullable=False, unique=True)
    notes = Column(String(2000), nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    deliveries = relationship("Delivery", back_populates="factory")
    requirements = relationship("FactoryRequirement", back_populates="factory", cascade="all, delete-orphan")
    cards = relationship("FactoryCard", back_populates="factory", cascade="all, delete-orphan")
    payments = relationship("FactoryPayment", back_populates="factory", cascade="all, delete-orphan")

class FactoryRequirement(Base):
    __tablename__ = "factory_requirements"
    id = Column(Integer, primary_key=True)
    factory_id = Column(Integer, ForeignKey("factories.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    required_unit = Column(String(50), nullable=True)  # if factory needs specific unit type
    notes = Column(String(2000), nullable=True)

    factory = relationship("Factory", back_populates="requirements")
    item = relationship("Item")

    __table_args__ = (
        UniqueConstraint('factory_id', 'item_id', name='uq_factory_item_req'),
    )

class FactoryCard(Base):
    __tablename__ = "factory_cards"
    id = Column(Integer, primary_key=True)
    factory_id = Column(Integer, ForeignKey("factories.id"), nullable=False)
    grade = Column(String(100), nullable=True)
    gross_weight = Column(Float, nullable=False)
    discount_percent = Column(Float, nullable=False, default=0.0)
    net_weight = Column(Float, nullable=False)
    price_today = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    factory = relationship("Factory", back_populates="cards")

# =============================
# Transactions
# =============================
class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True)
    invoice_no = Column(String(100), nullable=True, unique=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    customer_name = Column(String(500), nullable=True)
    total_amount = Column(Float, nullable=False, default=0.0)
    discount_amount = Column(Float, nullable=False, default=0.0)
    tax_amount = Column(Float, nullable=False, default=0.0)
    net_amount = Column(Float, nullable=False, default=0.0)
    status = Column(String(50), nullable=False, default="draft")  # draft/posted
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    supplier = relationship("Supplier")
    lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")

class InvoiceLine(Base):
    __tablename__ = "invoice_lines"
    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    description = Column(String(1000), nullable=True)
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False, default="kg")
    unit_price = Column(Float, nullable=False)
    discount = Column(Float, nullable=False, default=0.0)
    line_total = Column(Float, nullable=False)

    invoice = relationship("Invoice", back_populates="lines")
    item = relationship("Item")

class Delivery(Base):
    __tablename__ = "deliveries"
    id = Column(Integer, primary_key=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    factory_id = Column(Integer, ForeignKey("factories.id"), nullable=True)

    quantity = Column(Float, nullable=False)                 # quantity in unit
    unit = Column(String(50), nullable=False, default="kg") # unit used for this delivery
    unit_weight = Column(Float, nullable=True)               # optional effective weight per unit (e.g., bag weight)

    price_per_unit = Column(Float, nullable=False)           # price per unit used
    total_price = Column(Float, nullable=False)              # computed = quantity * price_per_unit

    delivered_at = Column(DateTime, default=datetime.now(timezone.utc))

    supplier = relationship("Supplier", back_populates="deliveries")
    item = relationship("Item", back_populates="deliveries")
    factory = relationship("Factory", back_populates="deliveries")

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    amount = Column(Float, nullable=False)                 # amount paid to supplier (reduces balance)
    method = Column(String(100), nullable=True)             # cash/bank/etc.
    note = Column(String(1000), nullable=True)
    paid_at = Column(DateTime, default=datetime.now(timezone.utc))

    supplier = relationship("Supplier", back_populates="payments")

class FactoryPayment(Base):
    __tablename__ = "factory_payments"
    id = Column(Integer, primary_key=True)
    factory_id = Column(Integer, ForeignKey("factories.id"), nullable=False)
    amount = Column(Float, nullable=False)
    method = Column(String(100), nullable=True)
    note = Column(String(1000), nullable=True)
    paid_at = Column(DateTime, default=datetime.now(timezone.utc))

    factory = relationship("Factory", back_populates="payments")

# =============================
# App settings (removed licensing model)
# =============================
class AppSetting(Base):
    __tablename__ = "app_settings"
    key = Column(String(200), primary_key=True)
    value = Column(String(5000), nullable=True)

# ملاحظة: تم حذف جدول التراخيص License بالكامل من النماذج

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    username = Column(String(255), nullable=True)
    action = Column(String(100), nullable=False)  # create/update/delete
    entity = Column(String(100), nullable=False)
    entity_id = Column(Integer, nullable=True)
    details = Column(String(5000), nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))