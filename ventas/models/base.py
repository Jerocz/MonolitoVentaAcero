"""Clase base de los modelos del monolito."""
from django.db import models


class AutoValidado(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
