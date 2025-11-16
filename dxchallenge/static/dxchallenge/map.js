// main vector layer
var countryStyle = new ol.style.Style({
    fill: new ol.style.Fill({
        color: 'rgba(100, 100, 100, 0.3)',
    }),
    stroke: new ol.style.Stroke({
        color: '#319FD3',
        width: 1,
    }),
});
var labelStyle = new ol.style.Style({
    text: new ol.style.Text({
        font: '12px Calibri,sans-serif',
        fill: new ol.style.Fill({
            color: '#000',
        }),
        stroke: new ol.style.Stroke({
            color: '#fff',
            width: 3,
        }),
        overflow: true,
    }),
});
var style = [countryStyle, labelStyle];

var mapstyle = function (feature) {
    // place label on biggest polygon only
    var geom = feature.getGeometry();
    if (geom.getType() == 'MultiPolygon') {
        var polys = geom.getPolygons().sort(function(a, b) {
            var areaA = a.getArea();
            var areaB = b.getArea();
            return areaA > areaB ? -1 : areaA < areaB ? 1 : 0;
        });
        labelStyle.setGeometry(polys[0]);
    } else {
        labelStyle.setGeometry(geom);
    }

    // actual label
    var id = feature.get('cty');
    //var count = feature.get('count');
    //if (count > 1) id += "\n" + count;
    labelStyle.getText().setText(id);

    // shape style
    /*
    if (color.value == "qsl") {
        if (feature.get('qsl') && feature.get('lotw')) {
            countryStyle.getFill().setColor(pattern(2, all_colors));
        } else if (feature.get('qsl')) {
            countryStyle.getFill().setColor('rgba(0, 0, 200, 0.3)');
        } else if (feature.get('lotw')) {
            countryStyle.getFill().setColor('rgba(0, 200, 0, 0.3)');
        } else {
            countryStyle.getFill().setColor('rgba(100, 100, 100, 0.3)');
        }
    } else if (color.value == "bands") {
        let summaryfeature = vectorSource.getFeatureById('summary');
        let all_bands = summaryfeature.getProperties()['bands'];
        countryStyle.getFill().setColor(make_pattern(all_bands, feature.get('bands')));
    } else if (color.value == "modes") {
        let summaryfeature = vectorSource.getFeatureById('summary');
        let all_modes = summaryfeature.getProperties()['modes'];
        countryStyle.getFill().setColor(make_pattern(all_modes, feature.get('modes')));
    } else if (color.value == "qso_via") {
        let summaryfeature = vectorSource.getFeatureById('summary');
        let all_qso_via = summaryfeature.getProperties()['qso_via'];
        countryStyle.getFill().setColor(make_pattern(all_qso_via, feature.get('qso_via')));
    } else if (color.value == "random") {
        countryStyle.getFill().setColor(random_color());
    } else {
    */
        countryStyle.getFill().setColor('rgba(100, 100, 100, 0.3)');
    //}

    return style;
};


var vectorSource = new ol.source.Vector({
    url: '/static/dxchallenge/dxcc.json',
    format: new ol.format.GeoJSON(),
});
var vectorLayer = new ol.layer.Vector({
    source: vectorSource,
    style: mapstyle,
});

const OSMSource = new ol.source.OSM({
    url: 'https://{a-c}.tile.openstreetmap.de/{z}/{x}/{y}.png',
    //attributions: [],
});

const map = new ol.Map({
    target: 'map',
    layers: [
        new ol.layer.Tile({ source: OSMSource, }),
        vectorLayer,
    ],
    view: new ol.View({
        center: [0, 0],
        zoom: 2,
        projection: ol.proj.get("EPSG:4326"),
    }),
});

// after loading, move all features (DXCC entities) to a dictionary
var dxcc = {};
var source_loaded = function(evt) {
    vectorSource.removeEventListener('change', source_loaded);
    vectorSource.forEachFeature(function(feature) {
        const id = feature.getProperties()['dxcc'];
        dxcc[id] = feature;
    });
    vectorSource.clear();
};
vectorSource.addEventListener('change', source_loaded);
