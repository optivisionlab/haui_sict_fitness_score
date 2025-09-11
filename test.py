from src.engine.score import GlobalEvaluator


ge = GlobalEvaluator([1,2,3,4], test_mode=True)  # chu trình 4 cam

# user đi đúng

ge.process_from_tracker([1], cam_id=1, timestamp=1)
print(ge.get_status(1))

ge.process_from_tracker([1], cam_id=2, timestamp=0)
print(ge.get_status(1)) 

ge.process_from_tracker([1], cam_id=3, timestamp=1)
print(ge.get_status(1)) 

ge.process_from_tracker([1], cam_id=4, timestamp=1)
print(ge.get_status(1)) 

ge.process_from_tracker([1], cam_id=1, timestamp=1)
print(ge.get_status(1))

ge.process_from_tracker([1], cam_id=2, timestamp=0)
print(ge.get_status(1)) 

ge.process_from_tracker([1], cam_id=3, timestamp=1)
print(ge.get_status(1)) 

ge.process_from_tracker([1], cam_id=4, timestamp=1)
print(ge.get_status(1)) 
