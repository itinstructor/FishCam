# ---------------------------- WEB PAGE HTML ------------------------------- #
""" This is the HTML code for the web page for testing in a browser.
 It's a multi-line string (triple quotes) so you can write it like a document."""
PAGE = """
<html>
<head>
<title>WNCC Aquaponics - Dual Camera Monitor</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body { 
    font-family: Arial, sans-serif; 
    margin: 20px; 
    background-color: #f0f0f0; 
}
.container { 
    max-width: 1200px; 
    margin: 0 auto; 
    background-color: white; 
    padding: 20px; 
    border-radius: 10px; 
    box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
}
.camera-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin: 20px 0;
}
.camera-box {
    background-color: #f8f9fa;
    border-radius: 8px;
    padding: 15px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}
.camera-title {
    text-align: center;
    margin-bottom: 10px;
    font-weight: bold;
    color: #555;
}
.camera-stream {
    width: 100%;
    height: auto;
    border: 2px solid #333;
    border-radius: 4px;
}
.info { 
    text-align: center;
    margin-top: 20px; 
    padding: 15px; 
    background-color: #e6f3ff; 
    border-radius: 5px; 
    font-size: 14px;
    color: #666;
}
@media (max-width: 768px) {
    .camera-grid {
        grid-template-columns: 1fr;
    }
}
</style>
</head>
<body>
<div class="container">
    <h1>WNCC Aquaponics - Dual Camera Monitor</h1>
    <p>Live video feeds from aquaponics system cameras</p>
    
    <div class="camera-grid">
        <div class="camera-box">
            <div class="camera-title">Camera 0 - Fish Tank View</div>
            <img src="/stream0.mjpg" class="camera-stream" alt="Camera 0 Stream">
        </div>
        <div class="camera-box">
            <div class="camera-title">Camera 1 - Plant Bed View</div>
            <img src="/stream1.mjpg" class="camera-stream" alt="Camera 1 Stream">
        </div>
    </div>
    
    <div class="info">
        <strong>Stream Info:</strong><br>
        Resolution: 1280x720 | Quality: High | Frame Rate: Up to 10 FPS<br>
        Optimized for aquaponics monitoring and reduced bandwidth usage<br>
        <p>Direct stream URLs: <a href="/stream0.mjpg">Camera 0</a> | <a href="/stream1.mjpg">Camera 1</a></p>
    </div>
</div>
</body>
</html>
"""