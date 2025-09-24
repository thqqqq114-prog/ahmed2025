from __future__ import annotations
from datetime import datetime, timedelta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
try:
    from PySide6.QtCharts import QChart, QChartView, QBarSet, QBarSeries, QBarCategoryAxis, QValueAxis
    CHARTS_AVAILABLE = True
except Exception:
    CHARTS_AVAILABLE = False
from app.data.database import SessionLocal
from app.data.models import Delivery, Payment

class DashboardPage(QWidget):
    """لوحة رئيسية: اختصارات + رسم بياني لحركة العمل آخر 30 يوم"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DashboardPage")
        self.setLayoutDirection(Qt.RightToLeft)

        root = QVBoxLayout(self)

        # اختصارات سريعة
        shortcuts = QHBoxLayout(); shortcuts.setAlignment(Qt.AlignRight)
        self.btn_go_journal = QPushButton("+ يومية")
        self.btn_go_factory_card = QPushButton("+ كارتة مصنع")
        self.btn_go_reports = QPushButton("التقارير")
        for b in (self.btn_go_journal, self.btn_go_factory_card, self.btn_go_reports):
            b.setMinimumHeight(36)
            shortcuts.addWidget(b)
        root.addLayout(shortcuts)

        # عنوان
        title = QLabel("حركة العمل خلال 30 يوم")
        title.setStyleSheet("font-size:18px; font-weight:bold; margin: 12px 0;")
        root.addWidget(title)

        # رسم بياني بسيط: إجمالي توريدات وإجمالي مدفوعات لكل يوم
        if CHARTS_AVAILABLE:
            chart_view = QChartView(self._build_chart())
            chart_view.setRenderHint(chart_view.renderHints())
            root.addWidget(chart_view, 1)
        else:
            note = QLabel("وحدة الرسوم QtCharts غير متاحة. يمكن إضافتها عبر تثبيت PySide6-Addons حسب النظام.")
            root.addWidget(note)

    def _build_chart(self) -> QChart:
        end = datetime.now().date()
        start = end - timedelta(days=29)
        days = [(start + timedelta(days=i)) for i in range(30)]
        cats = [d.strftime('%m-%d') for d in days]

        d_map = {d: 0.0 for d in days}
        p_map = {d: 0.0 for d in days}
        with SessionLocal() as s:
            # جمع التوريدات
            for d in s.query(Delivery).all():
                dt = d.delivered_at.date() if d.delivered_at else None
                if dt in d_map:
                    d_map[dt] += float(d.total_price or 0)
            # جمع المدفوعات
            for p in s.query(Payment).all():
                dt = p.paid_at.date() if p.paid_at else None
                if dt in p_map:
                    p_map[dt] += float(p.amount or 0)

        set_del = QBarSet("توريدات")
        set_pay = QBarSet("مدفوعات")
        set_del.append([d_map[d] for d in days])
        set_pay.append([p_map[d] for d in days])

        series = QBarSeries(); series.append(set_del); series.append(set_pay)
        chart = QChart(); chart.addSeries(series); chart.setTitle("")
        axisX = QBarCategoryAxis(); axisX.append(cats)
        axisY = QValueAxis(); axisY.setLabelFormat("%.0f"); axisY.setTitleText("القيمة")
        chart.addAxis(axisX, Qt.AlignBottom); chart.addAxis(axisY, Qt.AlignLeft)
        series.attachAxis(axisX); series.attachAxis(axisY)
        chart.legend().setVisible(True); chart.legend().setAlignment(Qt.AlignBottom)
        return chart