-- MySQL dump 10.13  Distrib 8.0.43, for Win64 (x86_64)
--
-- Host: localhost    Database: travel_crm
-- ------------------------------------------------------
-- Server version	8.3.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `activity_logs`
--

DROP TABLE IF EXISTS `activity_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `activity_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `action` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `entity_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `entity_id` int DEFAULT NULL,
  `details` text COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_created` (`created_at`),
  KEY `idx_user` (`user_id`),
  CONSTRAINT `activity_logs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=44 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `activity_logs`
--

LOCK TABLES `activity_logs` WRITE;
/*!40000 ALTER TABLE `activity_logs` DISABLE KEYS */;
INSERT INTO `activity_logs` VALUES (1,1,'LOGIN',NULL,NULL,'User admin logged in','2026-03-08 07:21:14'),(2,1,'LOGIN',NULL,NULL,'User admin logged in','2026-03-08 07:23:56'),(3,2,'LOGIN',NULL,NULL,'User neha logged in','2026-03-08 07:24:30'),(4,2,'CREATE_LEAD','lead',1,'Created lead LEAD-2026-00001','2026-03-08 07:28:16'),(5,1,'LOGIN',NULL,NULL,'User admin logged in','2026-03-08 07:35:10'),(6,2,'LOGIN',NULL,NULL,'User neha logged in','2026-03-08 07:36:05'),(7,2,'LOGIN',NULL,NULL,'User neha logged in','2026-03-08 07:42:09'),(8,1,'LOGIN',NULL,NULL,'User admin logged in','2026-03-08 07:48:10'),(9,2,'LOGIN',NULL,NULL,'User neha logged in','2026-03-08 07:51:54'),(10,2,'CREATE_BOOKING','booking',1,'Created booking BOOKING-2026-00001','2026-03-08 07:55:37'),(11,1,'LOGIN',NULL,NULL,'User admin logged in','2026-03-08 07:58:13'),(12,1,'ADD_CONVERSATION','lead',1,'Added conversation to lead 1','2026-03-08 07:59:47'),(13,2,'LOGIN',NULL,NULL,'User neha logged in','2026-03-08 08:00:58'),(14,1,'LOGIN',NULL,NULL,'User admin logged in','2026-03-08 08:02:44'),(15,1,'LOGIN',NULL,NULL,'User admin logged in','2026-03-08 08:04:22'),(16,2,'LOGIN',NULL,NULL,'User neha logged in','2026-03-08 08:08:02'),(17,2,'ADD_CONVERSATION','lead',1,'Added conversation to lead 1','2026-03-08 08:09:12'),(18,2,'ADD_CONVERSATION','lead',1,'Added conversation to lead 1','2026-03-08 08:10:18'),(19,2,'ADD_CONVERSATION','lead',1,'Added conversation to lead 1','2026-03-08 08:10:53'),(20,1,'LOGIN',NULL,NULL,'User admin logged in','2026-03-08 08:14:00'),(21,2,'LOGIN',NULL,NULL,'User neha logged in','2026-03-08 08:19:23'),(22,1,'LOGIN',NULL,NULL,'User admin logged in','2026-03-08 08:30:12'),(23,2,'LOGIN',NULL,NULL,'User neha logged in','2026-03-08 08:33:18'),(24,2,'UPDATE_LEAD','lead',1,'Updated lead 1','2026-03-08 08:34:30'),(25,1,'LOGIN',NULL,NULL,'User admin logged in','2026-03-08 08:34:59'),(26,1,'UPDATE_LEAD','lead',1,'Updated lead 1','2026-03-08 08:36:34'),(27,1,'LOGIN',NULL,NULL,'User admin logged in','2026-03-08 10:22:45'),(28,2,'LOGIN',NULL,NULL,'User neha logged in','2026-03-08 10:24:59'),(29,2,'ADD_CONVERSATION','lead',1,'Added conversation to lead 1','2026-03-08 10:26:20'),(30,1,'LOGIN',NULL,NULL,'User admin logged in','2026-03-08 10:26:56'),(31,2,'LOGIN',NULL,NULL,'User neha logged in','2026-03-08 10:52:53'),(32,2,'CREATE_LEAD','lead',2,'Created lead LEAD-2026-00002','2026-03-08 11:07:27'),(33,2,'ADD_CONVERSATION','lead',2,'Added conversation to lead 2','2026-03-08 11:09:22'),(34,1,'LOGIN',NULL,NULL,'User admin logged in','2026-03-08 11:10:00'),(35,2,'LOGIN',NULL,NULL,'User neha logged in','2026-03-08 13:22:56'),(36,2,'LOGIN',NULL,NULL,'User neha logged in','2026-03-08 18:13:41'),(37,1,'LOGIN',NULL,NULL,'User admin logged in','2026-03-08 18:14:13'),(38,2,'LOGIN',NULL,NULL,'User neha logged in','2026-03-08 18:17:40'),(39,1,'LOGIN',NULL,NULL,'User admin logged in','2026-03-14 13:19:52'),(40,2,'LOGIN',NULL,NULL,'User neha logged in','2026-03-14 13:21:01'),(41,2,'ADD_CONVERSATION','lead',1,'Added conversation to lead 1','2026-03-14 13:23:04'),(42,1,'LOGIN',NULL,NULL,'User admin logged in','2026-03-14 13:23:31'),(43,1,'LOGIN',NULL,NULL,'User admin logged in','2026-03-18 22:54:52');
/*!40000 ALTER TABLE `activity_logs` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-03-19  5:06:35
