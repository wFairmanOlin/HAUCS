let map;

// Function that styles the boxes given their last voltage
function boxStyle(sensor_id,voltage) {
  var mediumBatt = 3.8;
  var lowBatt = 3.6;
  let color = 'gray';

    if (voltage < lowBatt){
      color = 'red';
    }

    else if(voltage < mediumBatt){
      color = 'orange';
    }

    else {
      color = "green";
    }

    return color;
  }
  
// Function that initializes the map
function initMap() {
  var center = { lat: 27.5292996, lng: -80.3512828 };
  var map = new google.maps.Map(document.getElementById('map'), 
  {
    zoom: 20,
    center: center,
    mapTypeId: 'satellite',
    mapTypeControl: false,
    fullscreenControl: true,
    streetViewControl: false
  });

  // Load GeoJSON.
  map.data.addGeoJson(geoFile_bms);

  map.data.setStyle((feature) => {
    let sensor_id = feature.getProperty('number');
    let voltage = battVolt_bms[sensor_id]

    color = boxStyle(sensor_id, voltage)
   
    return /** @type {!google.maps.Data.StyleOptions} */ {
      fillColor: color,
      strokeColor: color,
      strokeWeight: 2,
    };
  });

  //Adding listeners for user interaction
  map.data.addListener("click", (event) => {
    location.href = "/sensor"+event.feature.getProperty("number");
  });

  map.data.addListener("mouseover", (event) => {
    map.data.revertStyle();
    map.data.overrideStyle(event.feature, { strokeWeight: 5 });
  });

  map.data.addListener("mouseout", (event) => {
    map.data.revertStyle();
  });
}

window.initMap = initMap;