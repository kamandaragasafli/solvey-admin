from django.db import models

# Create your models here.
class Region(models.Model):
    TYPE = [
    ('Bakı', 'Bakı'),
    ('Digər', 'Digər'),

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
    ('baku', 'Bakı'),
    ('ganja', 'Gəncə'),
    ('sumqayit', 'Sumqayıt'),
    ('mingachevir', 'Mingəçevir'),
    ('shirvan', 'Şirvan'),
    ('naftalan', 'Naftalan'),
    ('shamakhi', 'Şamaxı'),
    ('shusha', 'Şuşa'),
    ('yevlakh', 'Yevlax'),
    ('khankendi', 'Xankəndi'),
    ('khirdalan', 'Xırdalan'),
    ('lankaran', 'Lənkəran'),
    ('gazakh', 'Qazax'),
    ('dashkasan', 'Daşkəsən'),
    ('goygol', 'Göygöl'),
    ('goranboy', 'Goranboy'),
    ('terter', 'Tərtər'),
    ('zagatala', 'Zaqatala'),
    ('qakh', 'Qax'),
    ('oguz', 'Oğuz'),
    ('guba', 'Quba'),
    ('khachmaz', 'Xaçmaz'),
    ('kurdemir', 'Kürdəmir'),
    ('hajigabul', 'Hacıqabul'),
    ('sabirabad', 'Sabirabad'),
    ('saatli', 'Saatlı'),
    ('imisli', 'İmişli'),
    ('sabran', 'Şabran'),
    ('astara', 'Astara'),
    ('lerik', 'Lerik'),
    ('yardimli', 'Yardımlı'),
    ('masalli', 'Masallı'),
    ('jalilabad', 'Cəlilabad'),
    ('bilasuvar', 'Biləsuvar'),
    ('neftchala', 'Neftçala'),
    ('salyan', 'Salyan'),
    ('shaki', 'Şəki'),
    ('zardab', 'Zərdab'),
    ('agjabadi', 'Ağcabədi'),
    ('beylagan', 'Beyləqan'),
    ('fuzuli', 'Füzuli'),
    ('jabrayil', 'Cəbrayıl'),
    ('aghdam', 'Ağdam'),
    ('aghdash', 'Ağdaş'),
    ('gobustan', 'Qobustan'),
    ('shabran', 'Şabran'),
    ('shamkir', 'Şəmkir'),
    ('gusar', 'Qusar'),
    ('siyezen', 'Siyəzən'),
    ('balakan', 'Balakən'),
    ('samukh', 'Samux'),
    ('kalbajar', 'Kəlbəcər'),
    ('lachin', 'Laçın'),
    ('zangilan', 'Zəngilan'),
    ('qubadli', 'Qubadlı'),
    ('aghstafa', 'Ağstafa'),
    ('tovuz', 'Tovuz'),
    ('ismayilli', 'İsmayıllı'),
    ('sheki', 'Şəki'),
    ('dashkasan', 'Daşkəsən'),
]


    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name="cities")
    city_name = models.CharField(max_length=100, choices=CITY_CHOICES)

    class Meta:
        unique_together = ('region', 'city_name')  
        
    def __str__(self):
        return f"{self.region}-{self.city_name}"
    
    class Meta:
        verbose_name = "Şəhər"
        verbose_name_plural = "Şəhərlər "


   

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