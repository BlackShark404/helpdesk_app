# 🔐 AFTER LOGIN FLOW

## 1. Admin Page (Role: Admin)

### Dashboard Overview
- Total Students  
- Total Tickets  
- Total Staff Users  
- Last Ticket Created  

---

### Ticket Management
- **View all submitted tickets**
  - Ticket ID  
  - Student Name  
  - Issue  
  - Date Created  
- **Actions**
  - Delete ticket  
  - Mark ticket as resolved  

---

### Student Records
- **View full student information**
  - Student ID  
  - Name  
  - Email  
  - Phone Number *(visible only to Admin)*  

---

### Staff Management
- **View list of staff users**
  - ID  
  - Username  
  - Role  
  - Database User  

---

### Audit Logs
- **Show all actions on tickets**
  - Action Type *(Insert, Update, Delete)*  
  - Student ID  
  - Old Issue → New Issue  
  - Date and Time  

---

### Logout
- Ends current session  
- Returns to login page  

---

## 2. Support User Page (Role: Support)

### Dashboard Overview
- Open Tickets Count  
- Resolved Tickets Count  
- Registered Students Count  

---

### Ticket Queue
- **View all tickets assigned to support users**
  - Ticket ID  
  - Student Name  
  - Issue  
  - Status *(Open / Resolved)*  

---

### Sensitive Records (Limited Access)
- **View basic student data**
  - Student ID  
  - Name  
  - Email  
  - *(Phone number hidden — restricted by role)*  

---

### Audit Log (Read-Only)
- **View history of changes**
  - No edit permissions  

---

### Logout
- Ends current session  
- Returns to login page  
