# Generated by Django 4.2.18 on 2025-02-16 22:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Enrollment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "enrollment_date",
                    models.DateField(
                        auto_now_add=True,
                        help_text="Date the student enrolled in the course.",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("enrolled", "Enrolled"),
                            ("completed", "Completed"),
                            ("dropped", "Dropped"),
                        ],
                        default="enrolled",
                        help_text="Enrollment status.",
                        max_length=20,
                    ),
                ),
            ],
            options={
                "verbose_name": "Enrollment",
                "verbose_name_plural": "Enrollments",
                "db_table": "swarm_enrollment",
            },
        ),
        migrations.CreateModel(
            name="TeachingUnit",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        help_text="Unique code for the teaching unit (e.g., MTHS120).",
                        max_length=20,
                        unique=True,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Descriptive name of the teaching unit (e.g., Calculus).",
                        max_length=255,
                    ),
                ),
                (
                    "teaching_prompt",
                    models.TextField(
                        blank=True,
                        help_text="Instructions or guidelines for teaching this unit.",
                        null=True,
                    ),
                ),
            ],
            options={
                "verbose_name": "Teaching Unit",
                "verbose_name_plural": "Teaching Units",
                "db_table": "swarm_teachingunit",
            },
        ),
        migrations.CreateModel(
            name="Topic",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(help_text="Name of the topic.", max_length=255),
                ),
                (
                    "teaching_prompt",
                    models.TextField(
                        blank=True,
                        help_text="Instructions or guidelines for teaching this topic.",
                        null=True,
                    ),
                ),
                (
                    "teaching_unit",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="topics",
                        to="blueprints_university.teachingunit",
                    ),
                ),
            ],
            options={
                "verbose_name": "Topic",
                "verbose_name_plural": "Topics",
                "db_table": "swarm_topic",
            },
        ),
        migrations.CreateModel(
            name="Subtopic",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(help_text="Name of the subtopic.", max_length=255),
                ),
                (
                    "teaching_prompt",
                    models.TextField(
                        blank=True,
                        help_text="Instructions or guidelines for teaching this subtopic.",
                        null=True,
                    ),
                ),
                (
                    "topic",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subtopics",
                        to="blueprints_university.topic",
                    ),
                ),
            ],
            options={
                "verbose_name": "Subtopic",
                "verbose_name_plural": "Subtopics",
                "db_table": "swarm_subtopic",
            },
        ),
        migrations.CreateModel(
            name="Student",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Full name of the student.", max_length=255
                    ),
                ),
                (
                    "gpa",
                    models.DecimalField(
                        decimal_places=2,
                        default=0.0,
                        help_text="Grade point average of the student.",
                        max_digits=3,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("idle", "Idle")],
                        default="active",
                        help_text="Current status of the student.",
                        max_length=10,
                    ),
                ),
                (
                    "teaching_units",
                    models.ManyToManyField(
                        help_text="Teaching Units the student is enrolled in.",
                        related_name="students",
                        through="blueprints_university.Enrollment",
                        to="blueprints_university.teachingunit",
                    ),
                ),
            ],
            options={
                "verbose_name": "Student",
                "verbose_name_plural": "Students",
                "db_table": "swarm_student",
            },
        ),
        migrations.CreateModel(
            name="LearningObjective",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        help_text="Detailed description of the learning objective."
                    ),
                ),
                (
                    "topic",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="learning_objectives",
                        to="blueprints_university.topic",
                    ),
                ),
            ],
            options={
                "verbose_name": "Learning Objective",
                "verbose_name_plural": "Learning Objectives",
                "db_table": "swarm_learningobjective",
            },
        ),
        migrations.AddField(
            model_name="enrollment",
            name="student",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="enrollments",
                to="blueprints_university.student",
            ),
        ),
        migrations.AddField(
            model_name="enrollment",
            name="teaching_unit",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="enrollments",
                to="blueprints_university.teachingunit",
            ),
        ),
        migrations.CreateModel(
            name="Course",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Name of the course (e.g., Bachelor of Science).",
                        max_length=255,
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        help_text="Unique code for the course (e.g., BSCI).",
                        max_length=20,
                        unique=True,
                    ),
                ),
                (
                    "coordinator",
                    models.CharField(
                        help_text="Name of the course coordinator.", max_length=255
                    ),
                ),
                (
                    "teaching_prompt",
                    models.TextField(
                        blank=True,
                        help_text="Instructions or guidelines for teaching this course.",
                        null=True,
                    ),
                ),
                (
                    "teaching_units",
                    models.ManyToManyField(
                        help_text="Teaching units included in this course.",
                        related_name="courses",
                        to="blueprints_university.teachingunit",
                    ),
                ),
            ],
            options={
                "verbose_name": "Course",
                "verbose_name_plural": "Courses",
                "db_table": "swarm_course",
            },
        ),
        migrations.CreateModel(
            name="AssessmentItem",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "title",
                    models.CharField(
                        help_text="Title of the assessment (e.g., 'Midterm Exam').",
                        max_length=255,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "Pending"), ("completed", "Completed")],
                        default="pending",
                        help_text="Completion status of the assessment.",
                        max_length=20,
                    ),
                ),
                (
                    "due_date",
                    models.DateTimeField(
                        help_text="Due date and time for the assessment."
                    ),
                ),
                (
                    "weight",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Weight of the assessment as a percentage (e.g., 20.00).",
                        max_digits=5,
                    ),
                ),
                (
                    "submission_date",
                    models.DateTimeField(
                        blank=True,
                        help_text="Date and time the assessment was submitted.",
                        null=True,
                    ),
                ),
                (
                    "enrollment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assessments",
                        to="blueprints_university.enrollment",
                    ),
                ),
            ],
            options={
                "verbose_name": "Assessment Item",
                "verbose_name_plural": "Assessment Items",
                "db_table": "swarm_assessmentitem",
                "ordering": ["due_date"],
            },
        ),
        migrations.AlterUniqueTogether(
            name="enrollment",
            unique_together={("student", "teaching_unit")},
        ),
    ]
