provider "aws" {
  region = "ap-south-1"
}

# VPC


resource "aws_vpc" "my_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true

  tags = {
    Name = "django-vpc"
  }
}

# INTERNET GATEWAY

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.my_vpc.id
}

# PUBLIC SUBNET (load balancer + Nat Gateway)

resource "aws_subnet" "public_subnet_1" {
  vpc_id                  = aws_vpc.my_vpc.id
  cidr_block              = "10.0.0.0/24"
  availability_zone       = "ap-south-1a"
  map_public_ip_on_launch = true

  tags = {
    Name = "public-subnet_1"
  }
}

resource "aws_subnet" "public_subnet_2" {
  vpc_id                  = aws_vpc.my_vpc.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "ap-south-1b"
  map_public_ip_on_launch = true

  tags = {
    Name = "public-subnet_2"
  }
}

# PRIVATE SUBNET 2 for rds 2 for ec2

resource "aws_subnet" "private_subnet_1" {
  vpc_id            = aws_vpc.my_vpc.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "ap-south-1a"

  tags = {
    Name = "private-subnet_1"
  }
}

resource "aws_subnet" "private_subnet_2" {
  vpc_id            = aws_vpc.my_vpc.id
  cidr_block        = "10.0.3.0/24"
  availability_zone = "ap-south-1b"

  tags = {
    Name = "private-subnet_2"
  }
}

resource "aws_subnet" "private_subnet_rds_1" {
  vpc_id            = aws_vpc.my_vpc.id
  cidr_block        = "10.0.4.0/24"
  availability_zone = "ap-south-1a"

  tags = {
    Name = "private-subnet-rds-1"
  }
}

resource "aws_subnet" "private_subnet_rds_2" {
  vpc_id            = aws_vpc.my_vpc.id
  cidr_block        = "10.0.5.0/24"
  availability_zone = "ap-south-1b"

  tags = {
    Name = "private-subnet-rds-2"
  }
}

# PUBLIC ROUTE TABLE

resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.my_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
}

resource "aws_route_table_association" "public_assoc_1" {
  subnet_id      = aws_subnet.public_subnet_1.id
  route_table_id = aws_route_table.public_rt.id
}

resource "aws_route_table_association" "public_assoc_2" {
  subnet_id      = aws_subnet.public_subnet_2.id
  route_table_id = aws_route_table.public_rt.id
}

# ELASTIC IP

resource "aws_eip" "nat_eip" {
  domain = "vpc"
}

# NAT GATEWAY

resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat_eip.id
  subnet_id     = aws_subnet.public_subnet_1.id

  depends_on = [
    aws_internet_gateway.igw
  ]
}

# PRIVATE ROUTE TABLE

resource "aws_route_table" "private_rt" {
  vpc_id = aws_vpc.my_vpc.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat.id
  }
}

resource "aws_route_table_association" "private_assoc_1" {
  subnet_id      = aws_subnet.private_subnet_1.id
  route_table_id = aws_route_table.private_rt.id
}

resource "aws_route_table_association" "private_assoc_2" {
  subnet_id      = aws_subnet.private_subnet_2.id
  route_table_id = aws_route_table.private_rt.id
}

resource "aws_route_table_association" "private_subnet_rds_1" {
  subnet_id      = aws_subnet.private_subnet_rds_1.id
  route_table_id = aws_route_table.private_rt.id
}

resource "aws_route_table_association" "private_subnet_rds_2" {
  subnet_id      = aws_subnet.private_subnet_rds_2.id
  route_table_id = aws_route_table.private_rt.id
}

# EC2 SECURITY GROUP

resource "aws_security_group" "ec2_sg" {
  name   = "ec2-sg"
  vpc_id = aws_vpc.my_vpc.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description     = "Django"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ALB SECURITY GROUP

resource "aws_security_group" "alb_sg" {
  name   = "alb-sg"
  vpc_id = aws_vpc.my_vpc.id


  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "https"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# RDS SECURITY GROUP

resource "aws_security_group" "rds_sg" {
  name   = "rds-sg"
  vpc_id = aws_vpc.my_vpc.id

  ingress {
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# DB SUBNET GROUP

resource "aws_db_subnet_group" "db_subnet_group" {
  name = "db-subnet-group"

  subnet_ids = [
    aws_subnet.private_subnet_rds_1.id,
    aws_subnet.private_subnet_rds_2.id
  ]
}

# RDS MYSQL

resource "aws_db_instance" "mysql_db" {

  identifier = "django-db"

  engine         = "mysql"
  engine_version = "8.0"

  instance_class = "db.t3.micro"

  allocated_storage = 20

  db_name  = "mydb"
  username = "admin"
  password = "Pass123456"

  publicly_accessible = false

  skip_final_snapshot = true

  db_subnet_group_name = aws_db_subnet_group.db_subnet_group.name

  vpc_security_group_ids = [
    aws_security_group.rds_sg.id
  ]
}

# S3 Bucket

resource "aws_s3_bucket" "my_buck" {
  bucket        = "my-bucket-20-06-2006"
  force_destroy = true
}

# S3 Versioning

resource "aws_s3_bucket_versioning" "my_buck_ver" {

  bucket = aws_s3_bucket.my_buck.id

  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Lifecycle

resource "aws_s3_bucket_lifecycle_configuration" "my_buck_lifecycle" {

  bucket = aws_s3_bucket.my_buck.id

  rule {
    id     = "archive-and-delete"
    status = "Enabled"

    filter {}

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}

# Load Balancer

resource "aws_lb" "alb" {
  name               = "my-alb"
  load_balancer_type = "application"
  subnets            = [aws_subnet.public_subnet_1.id, aws_subnet.public_subnet_2.id]
  security_groups    = [aws_security_group.alb_sg.id]
}

# Target Group

resource "aws_lb_target_group" "tg" {
  name     = "tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = aws_vpc.my_vpc.id
}

# Listener

resource "aws_lb_listener" "listener" {
  load_balancer_arn = aws_lb.alb.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.tg.arn
  }
}

# IAM Role

resource "aws_iam_role" "ec2_role" {

  name = "django-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect = "Allow"

        Principal = {
          Service = "ec2.amazonaws.com"
        }

        Action = "sts:AssumeRole"
      }
    ]
  })
}

# IAM Policy

resource "aws_iam_policy" "ec2_policy" {

  name        = "django-ec2-policy"
  description = "Allow S3 and CloudWatch access"

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [

      {
        Effect = "Allow"

        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]

        Resource = [
          aws_s3_bucket.my_buck.arn,
          "${aws_s3_bucket.my_buck.arn}/*"
        ]
      },

      {
        Effect = "Allow"

        Action = [
          "cloudwatch:PutMetricData",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]

        Resource = "*"
      }
    ]
  })
}

# Policy Attachment

resource "aws_iam_role_policy_attachment" "ec2_attachment" {

  role = aws_iam_role.ec2_role.name

  policy_arn = aws_iam_policy.ec2_policy.arn
}

# Instance Profile

resource "aws_iam_instance_profile" "ec2_profile" {

  name = "django-ec2-profile"

  role = aws_iam_role.ec2_role.name
}

# Launch Template

resource "aws_launch_template" "app_lt" {

  name_prefix = "django-app-"

  image_id      = "ami-0f559c3642608c138"
  instance_type = "t3.micro"

  vpc_security_group_ids = [
    aws_security_group.ec2_sg.id
  ]

  iam_instance_profile {
    arn = aws_iam_instance_profile.ec2_profile.arn
  }

  monitoring {
    enabled = true
  }

  user_data = base64encode(<<-EOF
#!/bin/bash

yum update -y

yum install docker -y

sudo dnf install mariadb105 -y
yum dnf install mysql -y

systemctl enable docker
systemctl start docker

usermod -aG docker ec2-user

EOF
  )

  tag_specifications {
    resource_type = "instance"

    tags = {
      Name = "Django-App"
    }
  }
}

resource "aws_autoscaling_group" "app_asg" {

  name = "django-asg"

  min_size         = 2
  desired_capacity = 2
  max_size         = 4

  vpc_zone_identifier = [
    aws_subnet.private_subnet_1.id,
    aws_subnet.private_subnet_2.id
  ]
  target_group_arns = [
    aws_lb_target_group.tg.arn
  ]
  health_check_type         = "EC2"
  health_check_grace_period = 300

  launch_template {
    id      = aws_launch_template.app_lt.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "ASG-Django-App"
    propagate_at_launch = true
  }
}

resource "aws_autoscaling_policy" "scale_out" {

  name                   = "scale-out-policy"
  autoscaling_group_name = aws_autoscaling_group.app_asg.name

  adjustment_type    = "ChangeInCapacity"
  scaling_adjustment = 1
  cooldown           = 300
}

resource "aws_autoscaling_policy" "scale_in" {

  name                   = "scale-in-policy"
  autoscaling_group_name = aws_autoscaling_group.app_asg.name

  adjustment_type    = "ChangeInCapacity"
  scaling_adjustment = -1
  cooldown           = 300
}

resource "aws_cloudwatch_metric_alarm" "high_cpu" {

  alarm_name          = "high-cpu-alarm"
  comparison_operator = "GreaterThanThreshold"

  evaluation_periods = 2
  metric_name        = "CPUUtilization"
  namespace          = "AWS/EC2"
  period             = 120
  statistic          = "Average"

  threshold = 70

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.app_asg.name
  }

  alarm_actions = [
    aws_autoscaling_policy.scale_out.arn
  ]
}

resource "aws_cloudwatch_metric_alarm" "low_cpu" {

  alarm_name          = "low-cpu-alarm"
  comparison_operator = "LessThanThreshold"

  evaluation_periods = 2
  metric_name        = "CPUUtilization"
  namespace          = "AWS/EC2"
  period             = 120
  statistic          = "Average"

  threshold = 20

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.app_asg.name
  }

  alarm_actions = [
    aws_autoscaling_policy.scale_in.arn
  ]
}

# output "ec2_public_ip" {
#   value = aws_instance.django_server.public_ip
# }

output "rds_endpoint" {
  value = aws_db_instance.mysql_db.endpoint
}
/*
when we can create our own vpc then we need to create internet gateway
and also give route table and assosiation to access our subnet

1 > used for login on a server
ssh -i "trupal-key.pem" ec2-user@ec2-13-233-159-140.ap-south-1.compute.amazonaws.com

2 > download mariadb
sudo dnf install mariadb105 -y

3 > install mysql
sudo dnf install mysql -y

4 > this is for login on mysql
mysql -h terraform-20260424120940183200000001.c1sg6qq0gn4g.ap-south-1.rds.amazonaws.com -P 3306 -u admin -p
*/