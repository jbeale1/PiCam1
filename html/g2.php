<?php
function createGallery( $pathToImages, $pathToThumbs, $rThumbs )
{
  echo "Creating 200-element Image Gallery g2.html... <br />";

  $output = "<html>";
  $output .= "<head><title>Thumbnails</title></head>";
  $output .= "<body>";
  $output .= "<table cellspacing=\"0\" cellpadding=\"2\" width=\"500\">";
  $output .= "<tr>";

  // get array of filenames sorted in order
  $files = scandir( $pathToThumbs, 1 );

  $count = 0;
  $a=array();  // hold filenames in array so we can sort them in order
  // loop through the directory
  foreach ($files as $fname )
  {
    // strip the . and .. entries out
    if ($fname != '.' && $fname != '..' && ($count < 200) )
    {
      $a[]=$fname;  // add this filename to the array
      $count = $count + 1;
    }
  }

  $counter = 0;
  sort($a);  // sorts the array of filenames in-place
  foreach($a as $fname){
      $output .= "<td valign=\"middle\" align=\"center\"><a href=\"{$fname}\">";
      $output .= "<img src=\"{$rThumbs}{$fname}\" border=\"0\" />";
      $output .= "</a></td>";

      $counter += 1;
      if ( $counter % 5 == 0 ) { $output .= "</tr><tr>"; }
  }


  $output .= "</tr>";
  $output .= "</table>";
  $output .= "</body>";
  $output .= "</html>";

  // open the file
  $fhandle = fopen( "{$pathToImages}g2.html", "w" );
  // write the contents of the $output variable to the file
  fwrite( $fhandle, $output );
  // close the file
  fclose( $fhandle );
  echo "Done! <br>";
  echo "<a href=\"events/g2.html\" > view gallery </a>";
}
// call createGallery function and pass to it as parameters the path
// to the directory that contains images and the path to the directory
// in which thumbnails will be placed. We are assuming that
// the path will be a relative path working
// both in the filesystem, and through the web for links
createGallery("events/","events/thumbs/","thumbs/");
?>
