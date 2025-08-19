import requests
import streamlit as st
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from dotenv import load_dotenv
load_dotenv()

class LeaveManagementAPI:
    def __init__(self, base_url: str = st.secrets.get("API_BASE_URL", os.getenv("API_BASE_URL", "http://127.0.0.1:5000"))):
        self.base_url = base_url.rstrip('/')
        
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to the API with error handling"""
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method.upper() == 'GET':
                response = requests.get(url, timeout=10)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, timeout=10)
            elif method.upper() == 'PUT':
                response = requests.put(url, json=data, timeout=10)
            else:
                return {"success": False, "error": "Unsupported HTTP method"}
            
            return response.json()
        
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Cannot connect to API server"}
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            return {"success": False, "error": f"Request failed: {str(e)}"}

    def add_employee(self, name: str, email: str, department: str, joining_date: date) -> Dict[str, Any]:
        """Add a new employee"""
        data = {
            "name": name.strip(),
            "email": email.strip().lower(),
            "department": department.strip(),
            "joining_date": joining_date.strftime('%Y-%m-%d')
        }
        return self._make_request('POST', '/employees', data)

    def get_employees(self) -> Dict[str, Any]:
        """Get all employees"""
        return self._make_request('GET', '/employees')

    def get_employee(self, employee_id: int) -> Dict[str, Any]:
        """Get employee by ID"""
        return self._make_request('GET', f'/employees/{employee_id}')

    def apply_leave(self, 
                   employee_id: int, 
                   leave_type: str, 
                   start_date: date, 
                   end_date: date, 
                   reason: str = "") -> Dict[str, Any]:
        """Apply for leave"""
        data = {
            "employee_id": employee_id,
            "leave_type": leave_type,
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d'),
            "reason": reason.strip()
        }
        return self._make_request('POST', '/leave-requests', data)

    def get_leave_requests(self, 
                         employee_id: Optional[int] = None, 
                         status: Optional[str] = None) -> Dict[str, Any]:
        """Get leave requests with optional filters"""
        params = []
        if employee_id:
            params.append(f"employee_id={employee_id}")
        if status:
            params.append(f"status={status}")
            
        endpoint = '/leave-requests'
        if params:
            endpoint += f"?{'&'.join(params)}"
            
        return self._make_request('GET', endpoint)

    def approve_leave(self, request_id: int, approver_id: int) -> Dict[str, Any]:
        """Approve a leave request"""
        data = {"approved_by": approver_id}
        return self._make_request('PUT', f'/leave-requests/{request_id}/approve', data)

    def reject_leave(self, request_id: int, approver_id: int) -> Dict[str, Any]:
        """Reject a leave request"""
        data = {"approved_by": approver_id}
        return self._make_request('PUT', f'/leave-requests/{request_id}/reject', data)

    def get_leave_balance(self, employee_id: int) -> Dict[str, Any]:
        """Get employee leave balance"""
        return self._make_request('GET', f'/employees/{employee_id}/balance')

    def get_leave_history(self, 
                         employee_id: int, 
                         page: int = 1, 
                         limit: int = 10) -> Dict[str, Any]:
        """Get employee leave history"""
        return self._make_request('GET', 
                                f'/employees/{employee_id}/leave-history?page={page}&limit={limit}')

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics"""
        return self._make_request('GET', '/dashboard/stats')

class LeaveManagementUtils:
    def __init__(self):
        self.api = LeaveManagementAPI()
        
    def format_date(self, date_str: str) -> str:
        """Format date string to readable format"""
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            return dt.strftime('%B %d, %Y')
        except:
            return date_str
    
    def calculate_leave_duration(self, start_date: date, end_date: date) -> int:
        """Calculate working days between two dates"""
        days = 0
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:  # Monday = 0, Friday = 4
                days += 1
            current = current + timedelta(days=1)
        return days
    
    def validate_employee_data(self, 
                             name: str, 
                             email: str, 
                             department: str, 
                             joining_date: date) -> Dict[str, Any]:
        """Validate employee data before submission"""
        errors = []
        
        if not name or len(name.strip()) < 2:
            errors.append("Name must be at least 2 characters long")
            
        if not email or '@' not in email or '.' not in email:
            errors.append("Invalid email format")
            
        if not department or len(department.strip()) < 2:
            errors.append("Department must be at least 2 characters long")
            
        if joining_date > date.today():
            errors.append("Joining date cannot be in the future")
            
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def validate_leave_request(self, 
                             start_date: date, 
                             end_date: date, 
                             leave_type: str) -> Dict[str, Any]:
        """Validate leave request data"""
        errors = []
        
        if start_date > end_date:
            errors.append("Start date cannot be after end date")
            
        if start_date < date.today():
            errors.append("Cannot apply for leave on past dates")
            
        if leave_type not in ['annual', 'sick', 'emergency', 'maternity', 'paternity']:
            errors.append("Invalid leave type")
            
        working_days = self.calculate_leave_duration(start_date, end_date)
        if working_days == 0:
            errors.append("Leave duration must include working days")
        elif working_days > 30:
            errors.append("Leave duration cannot exceed 30 working days")
            
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "working_days": working_days
        }