
from django.urls import path
from medicine import views



urlpatterns = [
    path("addrugs/",views.medicine,name='med'),
    path("add-drug/",views.create_med,name='add-drug'),
    path("edit-drug/<int:id>/", views.update_drug, name="edit-drug"),
    path("delete-drug/<int:id>/",views.del_drug,name='remove'),
    path("drugs/",views.drugs,name='drugs'),
]
