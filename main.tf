provider "aws" {
  region ="ap-south-1"
}

#########################################
# VPC
#########################################

resource "aws_vpc" "my_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true

  tags = {
    Name = "django-vpc"
  }
}

#########################################
# INTERNET GATEWAY
#########################################

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.my_vpc.id
}

#########################################
# PUBLIC SUBNET
#########################################

resource "aws_subnet" "public_subnet" {
  vpc_id                  = aws_vpc.my_vpc.id
  cidr_block              = "10.0.0.0/24"
  availability_zone       = "ap-south-1a"
  map_public_ip_on_launch = true

  tags = {
    Name = "public-subnet"
  }
}

#########################################
# PRIVATE SUBNET
#########################################

resource "aws_subnet" "private_subnet" {
  vpc_id            = aws_vpc.my_vpc.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "ap-south-1b"

  tags = {
    Name = "private-subnet"
  }
}

#########################################
# PUBLIC ROUTE TABLE
#########################################

resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.my_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
}

resource "aws_route_table_association" "public_assoc" {
  subnet_id      = aws_subnet.public_subnet.id
  route_table_id = aws_route_table.public_rt.id
}

#########################################
# ELASTIC IP
#########################################

resource "aws_eip" "nat_eip" {
  domain = "vpc"
}

#########################################
# NAT GATEWAY
#########################################

resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat_eip.id
  subnet_id     = aws_subnet.public_subnet.id

  depends_on = [
    aws_internet_gateway.igw
  ]
}

#########################################
# PRIVATE ROUTE TABLE
#########################################

resource "aws_route_table" "private_rt" {
  vpc_id = aws_vpc.my_vpc.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat.id
  }
}

resource "aws_route_table_association" "private_assoc" {
  subnet_id      = aws_subnet.private_subnet.id
  route_table_id = aws_route_table.private_rt.id
}

#########################################
# EC2 SECURITY GROUP
#########################################

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
    description = "Django"
    from_port   = 8000
    to_port     = 8000
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

#########################################
# RDS SECURITY GROUP
#########################################

resource "aws_security_group" "rds_sg" {
  name   = "rds-sg"
  vpc_id = aws_vpc.my_vpc.id

  ingress {
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    cidr_blocks     = ["0.0.0.0/0"]
    security_groups = [aws_security_group.ec2_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

#########################################
# EC2 INSTANCE
#########################################

resource "aws_instance" "django_server" {

  ami           = "ami-048f4445314bcaa09"
  instance_type = "t3.micro"
  key_name      = "trupal-key"

  subnet_id                   = aws_subnet.public_subnet.id
  associate_public_ip_address = true

  vpc_security_group_ids = [
    aws_security_group.ec2_sg.id
  ]

  user_data = <<-EOF
    #!/bin/bash

    dnf update -y

    dnf install python3 python3-pip git nginx mariadb105 -y

    EOF

  tags = {
    Name = "django-server"
  }
}

#########################################
# DB SUBNET GROUP
#########################################

resource "aws_db_subnet_group" "db_subnet_group" {
  name = "db-subnet-group"

  subnet_ids = [
    aws_subnet.public_subnet.id,
    aws_subnet.private_subnet.id
  ]
}

#########################################
# RDS MYSQL
#########################################

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

output "ec2_public_ip" {
  value = aws_instance.django_server.public_ip
}

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