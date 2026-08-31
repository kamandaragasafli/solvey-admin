
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from decimal import Decimal, InvalidOperation
from medicine.models import Medical


def medicine(request):
    drug = Medical.objects.all()
    return render(request , "crud/add-order.html", {"drug":drug})


def create_med(request):
    if request.method == "POST":
        d_name = request.POST.get("drug_name", "").strip()
        d_full_name = request.POST.get("med_full_name", "").strip()
        d_price = request.POST.get("price")
        komissiya = request.POST.get("komissiya")

        if not d_name:
            messages.error(request, "Dərman adı mütləqdir.")
            return redirect("drugs")

        try:
            price = Decimal(d_price or "0")
            kom = Decimal(komissiya or "0")
        except (InvalidOperation, TypeError):
            messages.error(request, "Qiymət və ya komissiya düzgün deyil.")
            return redirect("drugs")

        Medical.objects.create(
            med_name=d_name,
            med_full_name=d_full_name or d_name,
            med_price=price,
            komissiya=kom,
        )
        messages.success(request, f"«{d_name}» əlavə olundu.")
        return redirect("drugs")

    return render(request, "crud/add-drug.html")


def update_drug(request, id):
    drug = get_object_or_404(Medical, id=id)
    if request.method != "POST":
        return redirect("drugs")

    d_name = request.POST.get("drug_name", "").strip()
    if not d_name:
        messages.error(request, "Dərman adı mütləqdir.")
        return redirect("drugs")

    try:
        price = Decimal(request.POST.get("price") or drug.med_price)
        kom = Decimal(request.POST.get("komissiya") or drug.komissiya)
        position = int(request.POST.get("position") or drug.position or 0)
    except (InvalidOperation, TypeError, ValueError):
        messages.error(request, "Qiymət, komissiya və ya sıra düzgün deyil.")
        return redirect("drugs")

    drug.med_name = d_name
    drug.med_full_name = request.POST.get("med_full_name", "").strip() or d_name
    drug.med_price = price
    drug.komissiya = kom
    drug.position = position
    drug.status = request.POST.get("status") == "1"
    drug.in_stock = request.POST.get("in_stock") == "1"
    drug.save()
    messages.success(request, f"«{drug.med_name}» yeniləndi.")
    return redirect("drugs")


def del_drug(request, id):
    rm_drug = get_object_or_404(Medical, id=id)
    rm_drug.delete()
    return redirect("drugs")





def drugs(request):
    drugs = Medical.objects.all().order_by("position")
    context ={
        "drugs": drugs
    }
    return render(request, "drugs.html", context)