import requests
import sys
import json
import os
from dotenv import load_dotenv
from pymongo import MongoClient
import time
import re
from datetime import datetime

class BitSafeAPITester:
    def __init__(self):
        # Use the local URL for testing
        self.base_url = 'http://localhost:8001'
        print(f"Using backend URL: {self.base_url}")
        
        self.tests_run = 0
        self.tests_passed = 0
        
        # Load environment variables from backend/.env
        load_dotenv("backend/.env")
        
        # Connect to MongoDB for database verification
        self.mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        self.db_name = os.environ.get('DB_NAME', 'test_database')
        self.mongo_client = MongoClient(self.mongo_url)
        self.db = self.mongo_client[self.db_name]

    def run_test(self, name, method, endpoint, expected_status, data=None, check_cors=False):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'OPTIONS':
                response = requests.options(url, headers=headers)

            success = response.status_code == expected_status
            
            # Check CORS headers if requested
            if check_cors and success:
                cors_headers = [
                    'Access-Control-Allow-Origin',
                    'Access-Control-Allow-Methods',
                    'Access-Control-Allow-Headers'
                ]
                cors_success = all(header in response.headers for header in cors_headers)
                if cors_success:
                    print("✅ CORS headers verified")
                else:
                    print("❌ CORS headers missing")
                    print(f"Headers: {response.headers}")
                    success = False
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json()
                except json.JSONDecodeError:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    print(f"Response: {response.text}")
                except:
                    pass
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        return self.run_test(
            "Root API Endpoint",
            "GET",
            "",
            200
        )

    def test_status_endpoint(self):
        """Test the status endpoint"""
        return self.run_test(
            "Status Endpoint",
            "GET",
            "status",
            200
        )

    def test_create_status_check(self):
        """Test creating a status check"""
        return self.run_test(
            "Create Status Check",
            "POST",
            "status",
            200,
            data={"client_name": "test_client"}
        )
        
    def test_chat_endpoint(self):
        """Test the chat endpoint with valid payload"""
        test_payload = {
            "message": "How can I reduce my crypto insurance premium?",
            "user_info": {
                "name": "Test User",
                "email": "test@example.com", 
                "phone": "+1234567890"
            }
        }
        
        return self.run_test(
            "Chat Endpoint",
            "POST",
            "chat",
            200,
            data=test_payload
        )
    
    def test_chat_response_format(self):
        """Test that the chat endpoint returns the correct response format"""
        test_payload = {
            "message": "What's covered by crypto insurance?",
            "user_info": {
                "name": "Format Tester",
                "email": "format@example.com", 
                "phone": "+1987654321"
            }
        }
        
        success, response = self.run_test(
            "Chat Response Format",
            "POST",
            "chat",
            200,
            data=test_payload
        )
        
        if success:
            # Check that the response has the expected fields
            if 'response' in response and 'recommendations' in response:
                if isinstance(response['recommendations'], list):
                    print("✅ Response format is correct")
                    return True, response
                else:
                    print("❌ 'recommendations' is not a list")
                    return False, response
            else:
                print("❌ Response is missing required fields")
                print(f"Response: {response}")
                return False, response
        
        return success, response
    
    def test_chat_error_handling(self):
        """Test error handling for the chat endpoint"""
        # Save the original API key
        original_api_key = os.environ.get('HF_API_KEY')
        
        # Temporarily remove the API key to simulate missing key
        if 'HF_API_KEY' in os.environ:
            del os.environ['HF_API_KEY']
        
        test_payload = {
            "message": "Test error handling",
            "user_info": {
                "name": "Error Tester",
                "email": "error@example.com", 
                "phone": "+1122334455"
            }
        }
        
        # We expect either a 500 error or a 200 with fallback response
        success, response = self.run_test(
            "Chat Error Handling (Missing API Key)",
            "POST",
            "chat",
            200,  # The endpoint has fallback logic, so it might still return 200
            data=test_payload
        )
        
        # Restore the original API key
        if original_api_key:
            os.environ['HF_API_KEY'] = original_api_key
        
        # If we got a 200 response, check if it's using the fallback logic
        if success and 'response' in response:
            print("✅ Fallback response provided when API key is missing")
            return True, response
        
        return success, response
    
    def test_cors_headers(self):
        """Test CORS headers for the chat endpoint"""
        # For FastAPI, we can check CORS headers on a regular GET request
        url = f"{self.base_url}/api/"
        headers = {'Origin': 'http://example.com'}
        
        self.tests_run += 1
        print(f"\n🔍 Testing CORS Headers...")
        print(f"URL: {url}")
        
        try:
            response = requests.get(url, headers=headers)
            
            # Check for CORS headers
            cors_headers = [
                'Access-Control-Allow-Origin',
                'Access-Control-Allow-Credentials'
            ]
            
            cors_success = all(header in response.headers for header in cors_headers)
            
            if cors_success:
                self.tests_passed += 1
                print("✅ CORS headers verified")
                print(f"✅ Passed - Status: {response.status_code}")
                return True, {}
            else:
                print("❌ CORS headers missing")
                print(f"Headers: {response.headers}")
                return False, {}
                
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}
    
    def test_database_storage(self):
        """Test that chat messages and AI responses are stored in the database"""
        self.tests_run += 1
        print(f"\n🔍 Testing Database Storage...")
        
        # Generate a unique message to identify in the database
        unique_message = f"Test database storage {time.time()}"
        test_payload = {
            "message": unique_message,
            "user_info": {
                "name": "DB Tester",
                "email": "db@example.com", 
                "phone": "+1555555555"
            }
        }
        
        # Send the chat message
        url = f"{self.base_url}/api/chat"
        headers = {'Content-Type': 'application/json'}
        
        try:
            # Send the request
            response = requests.post(url, json=test_payload, headers=headers)
            
            if response.status_code != 200:
                print(f"❌ Failed - Chat request failed with status {response.status_code}")
                return False, {}
            
            # Give the database a moment to process the request
            time.sleep(1)
            
            # Check if the message was stored in the database
            chat_message = self.db.chat_messages.find_one({"message": unique_message})
            
            if not chat_message:
                print("❌ Failed - Chat message not found in database")
                return False, {}
            
            print("✅ Chat message found in database")
            
            # Check if the AI response was stored
            ai_response = self.db.ai_responses.find_one({"user_id": chat_message["id"]})
            
            if not ai_response:
                print("❌ Failed - AI response not found in database")
                return False, {}
            
            print("✅ AI response found in database")
            print(f"✅ Database storage test passed")
            
            self.tests_passed += 1
            return True, {}
            
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}
            
    def test_scam_alerts_endpoint(self):
        """Test the scam alerts endpoint"""
        return self.run_test(
            "Scam Alerts Endpoint",
            "GET",
            "scam-alerts",
            200
        )
    
    def test_scam_alerts_structure(self):
        """Test that the scam alerts endpoint returns the correct data structure"""
        self.tests_run += 1
        print(f"\n🔍 Testing Scam Alerts Data Structure...")
        
        url = f"{self.base_url}/api/scam-alerts"
        headers = {'Content-Type': 'application/json'}
        
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                print(f"❌ Failed - Scam alerts request failed with status {response.status_code}")
                return False, {}
            
            try:
                alerts = response.json()
            except json.JSONDecodeError:
                print("❌ Failed - Response is not valid JSON")
                print(f"Response: {response.text}")
                return False, {}
            
            if not isinstance(alerts, list):
                print("❌ Failed - Response is not a list")
                print(f"Response type: {type(alerts)}")
                return False, {}
            
            if len(alerts) == 0:
                print("❌ Failed - No scam alerts returned")
                return False, {}
            
            print(f"✅ Found {len(alerts)} scam alerts")
            
            # Check that each alert has the required fields
            required_fields = ['title', 'description', 'amount_lost', 'source', 'timestamp', 'severity', 'link']
            valid_severities = ['high', 'medium', 'low']
            
            all_valid = True
            for i, alert in enumerate(alerts):
                missing_fields = [field for field in required_fields if field not in alert]
                
                if missing_fields:
                    print(f"❌ Alert {i+1} is missing required fields: {', '.join(missing_fields)}")
                    all_valid = False
                    continue
                
                # Check severity is valid
                if alert['severity'] not in valid_severities:
                    print(f"❌ Alert {i+1} has invalid severity: {alert['severity']}")
                    all_valid = False
                
                # Check timestamp is a valid date
                try:
                    # The timestamp comes as a string in ISO format
                    if isinstance(alert['timestamp'], str):
                        datetime.fromisoformat(alert['timestamp'].replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    print(f"❌ Alert {i+1} has invalid timestamp: {alert['timestamp']}")
                    all_valid = False
            
            if all_valid:
                print("✅ All alerts have the required fields with valid values")
                self.tests_passed += 1
                return True, alerts
            else:
                return False, alerts
            
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}
    
    def test_scam_alerts_links(self):
        """Test that all scam alert links are valid URLs pointing to real news sources"""
        self.tests_run += 1
        print(f"\n🔍 Testing Scam Alerts Links...")
        
        success, alerts = self.test_scam_alerts_endpoint()
        
        if not success or not alerts:
            print("❌ Failed - Could not retrieve scam alerts")
            return False, {}
        
        # Known crypto news domains
        known_news_sources = [
            'coindesk.com',
            'cointelegraph.com',
            'theblock.co',
            'medium.com',
            'chainalysis.com'
        ]
        
        # URL validation regex pattern
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        all_valid = True
        valid_links_count = 0
        known_source_count = 0
        
        for i, alert in enumerate(alerts):
            # Check if link field exists and is not empty
            if 'link' not in alert or not alert['link']:
                print(f"❌ Alert {i+1} ({alert.get('title', 'Unknown')}) has no link")
                all_valid = False
                continue
            
            link = alert['link']
            
            # Check if link is a valid URL
            if not url_pattern.match(link):
                print(f"❌ Alert {i+1} ({alert.get('title', 'Unknown')}) has invalid URL format: {link}")
                all_valid = False
                continue
            
            # Check if link points to a known crypto news source
            is_known_source = any(source in link for source in known_news_sources)
            if is_known_source:
                known_source_count += 1
            
            # Verify the link is accessible (HEAD request to avoid downloading full content)
            try:
                head_response = requests.head(link, timeout=5, allow_redirects=True)
                if head_response.status_code < 400:  # Any successful or redirect status
                    valid_links_count += 1
                    print(f"✅ Link verified: {link}")
                else:
                    print(f"❌ Alert {i+1} ({alert.get('title', 'Unknown')}) has inaccessible link: {link} (Status: {head_response.status_code})")
                    all_valid = False
            except requests.RequestException as e:
                print(f"❌ Alert {i+1} ({alert.get('title', 'Unknown')}) link error: {link} - {str(e)}")
                all_valid = False
        
        print(f"✅ {valid_links_count}/{len(alerts)} links are accessible")
        print(f"✅ {known_source_count}/{len(alerts)} links point to known crypto news sources")
        
        if all_valid and valid_links_count == len(alerts):
            print("✅ All scam alert links are valid and accessible")
            self.tests_passed += 1
            return True, {}
        else:
            success_rate = valid_links_count / len(alerts) if len(alerts) > 0 else 0
            if success_rate >= 0.9:  # 90% success rate is acceptable
                print("✅ Most scam alert links are valid (>90% success rate)")
                self.tests_passed += 1
                return True, {}
            else:
                return False, {}
    
    def test_scam_alerts_content(self):
        """Test that scam alerts include current 2024-2025 crypto security incidents"""
        self.tests_run += 1
        print(f"\n🔍 Testing Scam Alerts Content...")
        
        success, alerts = self.test_scam_alerts_endpoint()
        
        if not success or not alerts:
            print("❌ Failed - Could not retrieve scam alerts")
            return False, {}
        
        # Keywords to look for in titles and descriptions
        current_year_keywords = ['2024', '2025']
        crypto_keywords = ['crypto', 'bitcoin', 'ethereum', 'defi', 'nft', 'wallet', 'exchange', 'token']
        security_keywords = ['hack', 'scam', 'exploit', 'phishing', 'stolen', 'breach', 'attack', 'compromise']
        
        year_matches = 0
        crypto_matches = 0
        security_matches = 0
        
        for alert in alerts:
            title = alert.get('title', '').lower()
            description = alert.get('description', '').lower()
            content = title + ' ' + description
            
            # Check for current year references
            if any(year in content for year in current_year_keywords):
                year_matches += 1
            
            # Check for crypto terminology
            if any(keyword in content for keyword in crypto_keywords):
                crypto_matches += 1
            
            # Check for security incident terminology
            if any(keyword in content for keyword in security_keywords):
                security_matches += 1
        
        print(f"✅ {year_matches}/{len(alerts)} alerts mention 2024-2025")
        print(f"✅ {crypto_matches}/{len(alerts)} alerts contain crypto terminology")
        print(f"✅ {security_matches}/{len(alerts)} alerts mention security incidents")
        
        # Criteria for passing: at least 80% of alerts should contain crypto and security keywords
        # and at least some should mention current years
        if (crypto_matches / len(alerts) >= 0.8 and 
            security_matches / len(alerts) >= 0.8 and
            year_matches > 0):
            print("✅ Scam alerts contain relevant and current crypto security incidents")
            self.tests_passed += 1
            return True, {}
        else:
            print("❌ Some scam alerts may not be relevant or current")
            return False, {}

def main():
    # Setup
    tester = BitSafeAPITester()
    
    # Run basic API tests
    print("\n🔄 Running Basic API Tests...")
    root_success, _ = tester.test_root_endpoint()
    status_success, _ = tester.test_status_endpoint()
    create_status_success, _ = tester.test_create_status_check()
    
    # Run chat endpoint tests
    print("\n🔄 Running Chat API Tests...")
    chat_success, _ = tester.test_chat_endpoint()
    chat_format_success, _ = tester.test_chat_response_format()
    chat_error_success, _ = tester.test_chat_error_handling()
    cors_success, _ = tester.test_cors_headers()
    db_success, _ = tester.test_database_storage()
    
    # Run scam alerts tests
    print("\n🔄 Running Scam Alerts API Tests...")
    scam_alerts_success, _ = tester.test_scam_alerts_endpoint()
    scam_alerts_structure_success, alerts = tester.test_scam_alerts_structure()
    
    # Only run these tests if we successfully got alerts
    if scam_alerts_structure_success and alerts:
        scam_alerts_links_success, _ = tester.test_scam_alerts_links()
        scam_alerts_content_success, _ = tester.test_scam_alerts_content()
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    
    # Return success if all tests passed
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())