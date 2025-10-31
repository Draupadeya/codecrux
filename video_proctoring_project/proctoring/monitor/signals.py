from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import StudentProfile

@receiver(post_save, sender=StudentProfile)
def set_student_password(sender, instance, created, **kwargs):
    if created:
        dob_str = instance.dob.strftime('%Y%m%d')  # Format: YYYYMMDD
        user = instance.user
        user.set_password(dob_str)
        user.save()
