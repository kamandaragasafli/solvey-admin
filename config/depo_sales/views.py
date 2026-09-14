from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from .constants import CITY_COLOR, CITY_GROUPS, MERGED_BAKU_COLUMN, REFERENCE_CITIES
from .forms import UploadedReportForm
from .models import Drug, SalesRecord, UploadedReport
from .services.parser import parse_sales_workbook


def upload_report(request):
    """Excel faylını yüklə, parse et və DB-yə yaz, sonra hesabata yönləndir."""
    if request.method == "POST":
        form = UploadedReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save()
            try:
                _import_records(report)
            except Exception as exc:  # noqa: BLE001
                report.delete()
                messages.error(request, f"Fayl oxunarkən xəta baş verdi: {exc}")
                return redirect("depo_sales:upload")
            messages.success(request, "Hesabat uğurla yükləndi.")
            return redirect("depo_sales:report_detail", report_id=report.id)
    else:
        form = UploadedReportForm()

    reports = UploadedReport.objects.select_related("depo").all()[:20]
    return render(
        request,
        "depo_sales/upload.html",
        {"form": form, "reports": reports},
    )


def _import_records(report: UploadedReport) -> None:
    """Faylı parse edib Drug/SalesRecord obyektlərini yaradır."""
    parsed = parse_sales_workbook(report.file.path)

    records = []
    for drug_name, city_qty in parsed.items():
        drug, _ = Drug.objects.get_or_create(name=drug_name)
        for city, qty in city_qty.items():
            records.append(
                SalesRecord(report=report, drug=drug, city=city, quantity=qty)
            )
    SalesRecord.objects.bulk_create(records, ignore_conflicts=True)


def report_detail(request, report_id: int):
    report = get_object_or_404(UploadedReport, pk=report_id)
    matrix = _build_report_matrix(report)
    return render(
        request,
        "depo_sales/report.html",
        {"report": report, **matrix},
    )


def _build_report_matrix(report: UploadedReport) -> dict:
    """
    SalesRecord-lardan Excel-dəki kimi bir cədvəl strukturu qurur:
    Bakı+Abşeron -> istinad şəhərləri (qruplu, rəngli) -> əlavə şəhərlər -> cəm.
    """
    rows = (
        SalesRecord.objects.filter(report=report)
        .values("drug__name", "city")
        .annotate(total=Sum("quantity"))
    )

    by_drug: dict[str, dict[str, int]] = {}
    all_cities: set[str] = set()
    for row in rows:
        by_drug.setdefault(row["drug__name"], {})[row["city"]] = row["total"]
        all_cities.add(row["city"])

    reference_set = set(REFERENCE_CITIES)
    extra_cities = sorted(
        c for c in all_cities if c not in reference_set and c != MERGED_BAKU_COLUMN
    )
    final_cities = [MERGED_BAKU_COLUMN] + REFERENCE_CITIES + extra_cities

    headers = [
        {"name": city, "color": CITY_COLOR.get(city)}
        for city in final_cities
    ]

    drug_rows = []
    column_totals = {city: 0 for city in final_cities}
    grand_total = 0
    for drug_name in sorted(by_drug):
        city_qty = by_drug[drug_name]
        cells = []
        row_total = 0
        for city in final_cities:
            val = city_qty.get(city, 0)
            cells.append(val)
            column_totals[city] += val
            row_total += val
        grand_total += row_total
        drug_rows.append({"name": drug_name, "cells": cells, "total": row_total})

    group_totals = []
    for color, cities in CITY_GROUPS:
        group_totals.append(
            {
                "color": color,
                "span": len(cities),
                "total": sum(column_totals[c] for c in cities),
            }
        )

    extra_start_index = 1 + len(REFERENCE_CITIES)
    leading_blank = 3
    trailing_blank = (len(final_cities) - extra_start_index) + 1

    return {
        "headers": headers,
        "drug_rows": drug_rows,
        "column_totals": [column_totals[c] for c in final_cities],
        "group_totals": group_totals,
        "extra_start_index": extra_start_index,
        "leading_blank": leading_blank,
        "trailing_blank": trailing_blank,
        "grand_total": grand_total,
    }
