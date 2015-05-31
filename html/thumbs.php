<?php
//  from http://webcheatsheet.com/php/create_thumbnail_images.php
//  and http://php.net/manual/en/function.disk-total-space.php

function createThumbs( $pathToImages, $pathToThumbs, $thumbWidth )
{

  $df = disk_free_space("/media/sdb1");
  $dt = disk_total_space("/media/sdb1");
  $du = $dt - $df;
  $dp = sprintf('%.2f', ($du / $dt) * 100); // percent disk space used
  echo "working on ";
  // open the directory
  $dir = opendir( $pathToImages );

  $count = 0;  // how many images seen so far
  $a=array();  // hold filenames in array so we can sort them in order
  // loop through the directory
  while (false !== ($fname = readdir($dir)))
  {
    // parse path for the extension
    $info = pathinfo($pathToImages . $fname);

    // strip the . and .. entries out, use only .jpg files
    if ($fname != '.' && $fname != '..' && isset($info['extension']) && strtolower($info['extension']) == 'jpg' ) 
    {
      $a[]=$fname;  // add this filename to the array
      $count = $count + 1;
    }
  }
  echo "{$count} images... ";
  echo "disk: {$dp}%  <br />";

  // close the directory
  closedir( $dir );
  sort($a);  // sorts the array of filenames in-place

  // loop through files, looking for those not already done:
  foreach($a as $fname) {
    if ( true !== file_exists( "{$pathToThumbs}{$fname}" )) 
      {
       echo "Creating thumbnail for {$fname} <br />";

       // load image and get image size
       $img = imagecreatefromjpeg( "{$pathToImages}{$fname}" );
       $width = imagesx( $img );
       $height = imagesy( $img );

       // calculate thumbnail size
       $new_width = $thumbWidth;
       $new_height = floor( $height * ( $thumbWidth / $width ) );

       // create a new temporary image
       $tmp_img = imagecreatetruecolor( $new_width, $new_height );

       // copy and resize old image into new image
       imagecopyresized( $tmp_img, $img, 0, 0, 0, 0, $new_width, $new_height, $width, $height );

      // save thumbnail into a file
      imagejpeg( $tmp_img, "{$pathToThumbs}{$fname}" );
     } // end if-else
  }
  echo "Done! <br />";
  echo "<a href=\"g2.php\" > Create 200-img gallery</a> &nbsp; ";
  echo "<a href=\"gallery.php\" > Create full gallery</a> <br>";


} // end function createThumbs()

// call createThumb function and pass to it as parameters the path
// to the directory that contains images, the path to the directory
// in which thumbnails will be placed and the thumbnail's width.
// We are assuming that the path will be a relative path working
// both in the filesystem, and through the web for links
createThumbs("events/","events/thumbs/",200);
?>
