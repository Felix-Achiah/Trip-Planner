from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'address', 'phone_number', 'zip_code', 'created_at', 'is_active', 'password']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        email = validated_data.get('email', None)
        if not email:
            raise serializers.ValidationError({'email': 'This field is required.'})
        validated_data['email'] = email.lower()

        instance = self.Meta.model(**validated_data)

        if password is not None:
            try:
                validate_password(password, instance)
            except ValidationError as e:
                raise serializers.ValidationError({'password': e.messages})
                
            instance.set_password(password)
        instance.save()
        return instance