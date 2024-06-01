// Setup a white 3D screen with ortho projection
size(1000, 700, P3D);
background(255);
lights();
noStroke();
ortho();

// Move origin to pivot around the center 
// of the screen and draw our sphere
translate(width *0.5, height*0.5, 0);
sphere(280);

// Setup to draw the circle
noFill();
strokeWeight(3);
stroke(0);

for (float r = 0.0; r < 2*PI; r += PI/12) {
  pushMatrix();
  rotateY(r+PI/6);
  rotateZ(radians(37));
  rotateY(PI/2);
  circle(0, 0, 608);
  popMatrix();
 }
