// Draw simple orbits around a sphere

void setup() {
  // Setup 3D screen with ortho projection
  size(1000, 700, P3D);
  ortho();
}

void draw() {
  // White backround
  background(255);
  lights();

  // Move origin to pivot around the center 
  // of the screen and draw our sphere
  translate(width *0.5, height*0.5, 0);
  fill(255);
  noStroke(); // No outlines around the sphere
  sphere(280);

  // Setup to draw the orbit circles
  noFill(); // Only draw the outline
  strokeWeight(3);  // Use a 3 pixel thick line
  stroke(0); // Color the lines black 

  // Draw 24 orbit circles
  for (float r = 0.0; r < 2*PI; r += PI/12) {
    pushMatrix();
    // These take affect in a 'reverse' order (tricky)
    rotateY(r+PI/6); // Rotate to the orbit
    rotateZ(radians(37));  // incline 37 degrees
    rotateY(PI/2); // Turn sideways to rotate around Z axis
    circle(0, 0, 608);
    popMatrix();
    //break;  // uncomment to draw only one line
  }
}
