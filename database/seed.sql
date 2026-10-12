-- Sample Seed Data for CampusFinds
USE campusfinds;

-- Clear previous sample records if needed
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE handovers;
TRUNCATE TABLE claims;
TRUNCATE TABLE notifications;
TRUNCATE TABLE activity_logs;
TRUNCATE TABLE items;
TRUNCATE TABLE users;
SET FOREIGN_KEY_CHECKS = 1;

-- Users (All sample accounts have password: Password123!)
INSERT INTO users (id, full_name, email, phone, password_hash, role, student_id, department) VALUES
(1, 'Campus Admin', 'admin@rbunagpur.in', '+91-712-2550100', 'scrypt:32768:8:1$LniEODWnvGgInTCL$0b8e51837ae032408d575e6710bad5f8c018457021f24f0f65c708043d44248fb03b964df1c9232460ce7bbeb7eba845edf53a35ac9f7ef9eb9f0c4dac62f32f', 'admin', 'ADM-001', 'Campus Security & Facilities'),
(2, 'Alex Rivera', 'alex@rbunagpur.in', '+91-712-2550101', 'scrypt:32768:8:1$LniEODWnvGgInTCL$0b8e51837ae032408d575e6710bad5f8c018457021f24f0f65c708043d44248fb03b964df1c9232460ce7bbeb7eba845edf53a35ac9f7ef9eb9f0c4dac62f32f', 'student', 'RBU-CS-1029', 'Computer Science & Engg'),
(3, 'Samantha Reed', 'samantha@rbunagpur.in', '+91-712-2550102', 'scrypt:32768:8:1$LniEODWnvGgInTCL$0b8e51837ae032408d575e6710bad5f8c018457021f24f0f65c708043d44248fb03b964df1c9232460ce7bbeb7eba845edf53a35ac9f7ef9eb9f0c4dac62f32f', 'student', 'RBU-ME-2041', 'Mechanical Engineering'),
(4, 'David Chen', 'david@rbunagpur.in', '+91-712-2550103', 'scrypt:32768:8:1$LniEODWnvGgInTCL$0b8e51837ae032408d575e6710bad5f8c018457021f24f0f65c708043d44248fb03b964df1c9232460ce7bbeb7eba845edf53a35ac9f7ef9eb9f0c4dac62f32f', 'student', 'RBU-MBA-3312', 'Management Studies');

-- Items (Lost & Found)
INSERT INTO items (id, user_id, item_type, title, category, description, location, item_date, image_url, private_verification_details, status) VALUES
(1, 2, 'lost', 'Matte Black Apple AirPods Pro Case', 'Electronics', 'Lost my AirPods Pro 2nd Gen case near the central library 2nd floor silent study area.', 'Central Library 2nd Floor', '2026-10-09', NULL, 'Small scratch on top lid and has sticker of Pikachu underneath', 'open'),
(2, 3, 'found', 'AirPods Case with Pikachu Decal', 'Electronics', 'Found an AirPods case on the study desk in the Library. Handed to librarian desk temporarily.', 'Central Library 2nd Floor', '2026-10-09', NULL, 'Has a Pikachu sticker on the bottom and serial ending in 4921', 'open'),
(3, 3, 'lost', 'Dark Brown Leather Fossil Wallet', 'Personal Accessories', 'Lost my bi-fold brown leather wallet containing university ID and metro card.', 'Student Union Cafeteria', '2026-10-08', NULL, 'Contains Samantha Reed ID card and emergency $20 bill tucked in secret flap', 'open'),
(4, 4, 'found', 'Set of Keys with Blue Carabiner', 'Keys', 'Set of 3 dorm keys attached to a blue metal carabiner and a miniature brass guitar keychain.', 'Gymnasium Locker Room', '2026-10-10', NULL, 'Keys marked 304, RM-2, and Master. Guitar tag has name initials D.K.', 'open'),
(5, 2, 'lost', 'Calculus Early Transcendentals Hardcover', 'Books & Study Material', 'Stewart Calculus 9th edition textbook forgotten after math lecture.', 'Hall B Room 104', '2026-10-07', NULL, 'Name Alex Rivera written in ink on inner cover page 3', 'returned');

-- Claims
INSERT INTO claims (id, item_id, claimant_id, claim_description, proof_details, status, admin_or_finder_remarks, reviewed_by) VALUES
(1, 2, 2, 'These are definitely my AirPods case! I left them while studying for Midterms.', 'Inside sticker is yellow Pikachu with lightning bolt and case serial ends in 4921.', 'approved', 'Details matched exactly. Ready for handover at Central Library Helpdesk.', 1),
(2, 5, 2, 'Calculus textbook belongs to me.', 'Name Alex Rivera written on inner cover.', 'approved', 'Verified by Admin.', 1);

-- Handovers (for returned item 5)
INSERT INTO handovers (id, item_id, claim_id, handed_by, received_by, handover_date, location, notes) VALUES
(1, 5, 2, 1, 2, '2026-10-08 14:30:00', 'Campus Security Office', 'Handed over in person after verifying Student ID card.');

-- Notifications
INSERT INTO notifications (user_id, title, message, link, is_read) VALUES
(2, 'Claim Approved!', 'Your claim on AirPods Case with Pikachu Decal has been approved. Please arrange handover.', '/claims', 0),
(3, 'New Claim Submitted', 'Someone has submitted an ownership claim on your found item: AirPods Case with Pikachu Decal.', '/items/2', 0),
(2, 'Item Returned', 'Your Calculus book handover was completed successfully.', '/items/5', 1);

-- Activity Logs
INSERT INTO activity_logs (user_id, action, details, ip_address) VALUES
(1, 'SYSTEM_INIT', 'Database seeded with demo student and admin records.', '127.0.0.1'),
(2, 'ITEM_REPORTED', 'Alex Rivera reported lost item: Matte Black Apple AirPods Pro Case', '127.0.0.1'),
(3, 'ITEM_REPORTED', 'Samantha Reed reported found item: AirPods Case with Pikachu Decal', '127.0.0.1'),
(2, 'CLAIM_SUBMITTED', 'Alex Rivera submitted a claim on item #2', '127.0.0.1'),
(1, 'CLAIM_APPROVED', 'Admin approved claim #1 for item #2', '127.0.0.1');
