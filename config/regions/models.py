from django.db import models

# Create your models here.
class Region(models.Model):
    TYPE = [
    ('Bakı', 'Bakı'),
    ('Digər', 'Digər'),
    ('Şəhər', 'Şəhər'),

    ]
    region_name = models.CharField(max_length=100, unique=True)
    region_type = models.CharField(max_length=50, choices=TYPE, blank=True, null=True)

    def __str__(self):
        return self.region_name
    

    def doctors_count(self):
        return self.doctors.count()  # Doctor modelində region ForeignKey varsa

    def city_count(self):
        return self.cities.count()  # related_name="cities" olaraq qeyd olunub

    def hospital_count(self):
        return self.hospital_set.count()
    
    class Meta:
        verbose_name = "Bölgə"
        verbose_name_plural = "Bölgələr "

class City(models.Model):
    CITY_CHOICES = [
        ('Bakı', 'Bakı'),
        ('Gəncə', 'Gəncə'),
        ('Sumqayıt', 'Sumqayıt'),
        ('Mingəçevir', 'Mingəçevir'),
        ('Şirvan', 'Şirvan'),
        ('Naftalan', 'Naftalan'),
        ('Şamaxı', 'Şamaxı'),
        ('Şuşa', 'Şuşa'),
        ('Yevlax', 'Yevlax'),
        ('Xankəndi', 'Xankəndi'),
        ('Xırdalan', 'Xırdalan'),
        ('Lənkəran', 'Lənkəran'),
        ('Qazax', 'Qazax'),
        ('Daşkəsən', 'Daşkəsən'),
        ('Göygöl', 'Göygöl'),
        ('Goranboy', 'Goranboy'),
        ('Tərtər', 'Tərtər'),
        ('Zaqatala', 'Zaqatala'),
        ('Qax', 'Qax'),
        ('Oğuz', 'Oğuz'),
        ('Quba', 'Quba'),
        ('Xaçmaz', 'Xaçmaz'),
        ('Kürdəmir', 'Kürdəmir'),
        ('Hacıqabul', 'Hacıqabul'),
        ('Sabirabad', 'Sabirabad'),
        ('Saatlı', 'Saatlı'),
        ('İmişli', 'İmişli'),
        ('Şabran', 'Şabran'),
        ('Astara', 'Astara'),
        ('Lerik', 'Lerik'),
        ('Yardımlı', 'Yardımlı'),
        ('Masallı', 'Masallı'),
        ('Cəlilabad', 'Cəlilabad'),
        ('Biləsuvar', 'Biləsuvar'),
        ('Neftçala', 'Neftçala'),
        ('Salyan', 'Salyan'),
        ('Şəki', 'Şəki'),
        ('Zərdab', 'Zərdab'),
        ('Ağcabədi', 'Ağcabədi'),
        ('Beyləqan', 'Beyləqan'),
        ('Füzuli', 'Füzuli'),
        ('Cəbrayıl', 'Cəbrayıl'),
        ('Ağdam', 'Ağdam'),
        ('Ağdaş', 'Ağdaş'),
        ('Qobustan', 'Qobustan'),
        ('Şəmkir', 'Şəmkir'),
        ('Qusar', 'Qusar'),
        ('Siyəzən', 'Siyəzən'),
        ('Balakən', 'Balakən'),
        ('Samux', 'Samux'),
        ('Kəlbəcər', 'Kəlbəcər'),
        ('Laçın', 'Laçın'),
        ('Zəngilan', 'Zəngilan'),
        ('Qubadlı', 'Qubadlı'),
        ('Ağstafa', 'Ağstafa'),
        ('Tovuz', 'Tovuz'),
        ('İsmayıllı', 'İsmayıllı'),
    ]
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name="cities")
    city_name = models.CharField(max_length=100, choices=CITY_CHOICES)

    def __str__(self):
        return f"{self.region}-{self.city_name}"
    
    class Meta:
        unique_together = ('region', 'city_name')
        verbose_name = "Şəhər"
        verbose_name_plural = "Şəhərlər"


   

class Hospital(models.Model):
    hospital_name= models.CharField(max_length=100)
    region_net = models.ForeignKey(Region, on_delete=models.CASCADE)
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.hospital_name}-{self.region_net}"
    
    def city_count(self):
        return self.city.count()
    


    class Meta:
        verbose_name = "Xəstəxana/Klinika"
        verbose_name_plural = "Xəstəxana/Klinikalar "
        unique_together = ('hospital_name', 'region_net')