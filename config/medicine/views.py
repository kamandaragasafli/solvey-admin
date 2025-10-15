
from django.shortcuts import render, redirect, get_object_or_404
from medicine.models import Medical


def medicine(request):
    drug = Medical.objects.all()
    return render(request , "crud/add-order.html", {"drug":drug})


def create_med(request):
    if request.method == "POST":
        d_name   = request.POST.get("drug_name")
        d_price  = request.POST.get("price")
        komissiya  = request.POST.get("komissiya")  # düz ad

        if komissiya == "":
            komissiya = 0  # ya da istəyə uyğun boş olduqda sıfır ver

        Medical.objects.create(
            med_name=d_name,
            med_price=d_price,
            komissiya=komissiya
        )
        return redirect("drugs")

    return render(request, "crud/add-drug.html")

def del_drug(request, id):
    rm_drug = get_object_or_404(Medical, id=id)
    rm_drug.delete()
    return redirect("drugs")





def drugs(request):
    drugs = Medical.objects.all()
    context ={
        "drugs": drugs
    }
    return render(request, "drugs.html", context)