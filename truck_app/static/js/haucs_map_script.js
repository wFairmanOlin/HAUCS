let map;

// Function that initializes the map
async function initMap() {

  const { Map } = await google.maps.importLibrary("maps");

  map = new Map(document.getElementById('map'), 
  {
    zoom: 15,
    center: { lat: 37.705, lng: -89.458 },
    // tilt:45,
    mapTypeId: 'satellite',
    // rotateControl: true,
    // tiltControl: true,
    mapTypeControl: false,
    fullscreenControl: true,
    streetViewControl: false,
    
  }); 
  // Load GeoJSON.
  map.data.addGeoJson(geoFile_HAUCS);

  // Call style function
  map.data.setStyle((feature) => {
    let pond_id = feature.getProperty('number');
    let do_value = do_HAUCS['pond_' + pond_id]['last_do'];

    color = boxStyle(pond_id, do_value)
   
    return /** @type {!google.maps.Data.StyleOptions} */ {
      fillColor: color,
      strokeColor: color,
      strokeWeight: 2,
    };
});

  // Function that styles the boxes given their last voltage
  function boxStyle(pond_id, do_value) {
    var mediumDO = 80;
    var lowDO = 60;
    let color = 'gray';
      
      if (do_value > mediumDO){
        color = "green";
      }
      else if (do_value > lowDO){
        color = "orange";
      }
      else if (do_value > 0){
        color = "red";
      }

      return color;
  }  

  // Static aerators locations
  var marker_locations = [
    [ 37.7037823, -89.4648105],
    [ 37.703000518448896, -89.4688201254245]
  ];

  var infowindow = new google.maps.InfoWindow();

  // Initialize status and icon variables
  var status="on"; //will be a data point sent eventually
  var marker_icon = '';

  // Function that creates custom markers given locations
  function createMarkers(status, marker_locations, marker_icon){
    
    for(let i=0; i<marker_locations.length; i++){
      if (status=='on'){
        marker_icon = "static/images/aerator_on.svg";
      }
      else{
        marker_icon = "static/images/aerator_off.svg";
      }
      
      marker = new google.maps.Marker({
        position: new google.maps.LatLng(marker_locations[i][0], marker_locations[i][1]),
        map: map,
        icon: {
          url: marker_icon,
          scaledSize: new google.maps.Size(25,25)
        }
      });
      
      google.maps.event.addListener(marker, 'click', (function(marker, i){
        return function() {
          infowindow.setContent("Status: "+ status)
          infowindow.open(map, marker);
        }
      })(marker, i));
    }
  }

  // Call markers function
  // map_markers = createMarkers(status, marker_locations, marker_icon)

  // Add listeners for user interaction
  map.data.addListener("click", (event) => {
    location.href = "/pond"+event.feature.getProperty("number");
  });

  map.data.addListener("mouseover", (event) => {
    map.data.revertStyle();
    map.data.overrideStyle(event.feature, { strokeWeight: 5 });
    infowindow.setContent("pond " + event.feature.getProperty("number"));
    infowindow.setPosition(event.latLng);
    infowindow.setOptions({pixelOffset: new google.maps.Size(0,-10)});
    infowindow.open(map);
  });

  map.data.addListener("mouseout", (event) => {
    map.data.revertStyle();
    infowindow.close(map);
  });

}
// initMap();
window.initMap = initMap;