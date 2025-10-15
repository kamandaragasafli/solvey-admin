from django.db import models
from django.contrib.auth.models import User


class DeletedRecipeDrugLog(models.Model):
    drug_name = models.CharField(max_length=255)
    recipe_id = models.IntegerField()
    deleted_at = models.DateTimeField(auto_now_add=True)
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.drug_name} (Recipe ID: {self.recipe_id}) silindi {self.deleted_at}"
