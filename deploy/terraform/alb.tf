# Load Balancer removed for MVP
# Services are accessed directly via ECS task public IPs
# 
# To access services after deployment:
# 1. Go to AWS ECS Console
# 2. Click on your cluster -> Services -> Tasks
# 3. Click on a running task to see its public IP
# 4. Access: http://[PUBLIC_IP]:[PORT]
#   - Frontend: http://[IP]:80
#   - Backend: http://[IP]:8000/health