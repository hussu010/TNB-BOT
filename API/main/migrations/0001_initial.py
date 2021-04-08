# Generated by Django 3.1.7 on 2021-04-08 11:00

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Server',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ServerID', models.IntegerField()),
                ('ChannelID', models.IntegerField()),
                ('MoneyChannel', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Type', models.TextField()),
                ('TxID', models.TextField()),
                ('Amount', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('DiscordID', models.IntegerField()),
                ('Address', models.TextField()),
                ('Coins', models.IntegerField(default=0)),
            ],
        ),
    ]
