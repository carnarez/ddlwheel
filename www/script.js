import * as d3 from "https://cdn.skypack.dev/d3@7";

d3.json("data.json").then(rawData => {

  // https://observablehq.com/@d3/hierarchical-edge-bundling
  const drawDependencyWheel = (
    data, // json object
    {
      nodeColor = "#000", // link color
      linkColor = "#000", // link color
      linkColorIncoming = "#07f", // link color for parents
      linkColorOutgoing = "#f77", // link color for children
      radius = 200, // radius of the circle
      width = 800, // outer width, in pixels
      height = 800 // outer height, in pixels
    } = {}
  ) => {

    // generate the link between the objects
    const computeLine = (source, target) => {
      const line = d3.line()
        .curve(d3.curveBundle.beta(0.85));
      return line([[source.x, source.y], [0, 0], [target.x, target.y]]);
    }

    // generate the arc limiting the object source
    const computeArc = (radius, startAngle, endAngle) => {
      const arc = d3.arc()
        .innerRadius(radius - 1)
        .outerRadius(radius)
        .startAngle(startAngle)
        .endAngle(endAngle);
      return arc();
    }

    // scale the radius
    if (data.length > 100) radius *= 2;

    // coordinates are initially scaled to the radius
    const arcs = [],
          arcSpans = {},
          nodesPos = {},
          numNodes = data.length,
          angleArc = 2 * Math.PI / numNodes;

    // fix the font size
    let fontSize = parseInt(computedStyle.fontSize.replace("px", ""));
    if (Object.keys(data).length > 1) {
      fontSize = Math.min(2 * Math.sin(angleArc / 2) * radius, fontSize);
    }

    // compute all node coordinates
    for (let [i, d] of data.entries()) {
      let angle = i * angleArc - Math.PI / 2;
      nodesPos[d.name] = {
        "angle": angle,
        "x": radius * Math.cos(angle),
        "y": radius * Math.sin(angle)
      };
    }

    // compute arcs according to the number of objects shown
    for (let d of Object.keys(nodesPos)) {
      let [db, sc, ob] = d.split("."),
          key = "";

      if (data.length > 50) {
        key = db;
      } else {
        key = `${db}.${sc}`;
      }

      try {
        arcSpans[key].push(nodesPos[d].angle);
      } catch {
        arcSpans[key] = [nodesPos[d].angle];
      }
    }

    const availPos = Object.keys(nodesPos);

    // enrich the data with node coordinates: we need these to be on the unit circle
    // to avoid issues during rotations; nodes will be translated to their real
    // (radius-scaled) positions later on
    for (let d of data) {
      d.angle = nodesPos[d.name].angle * 180 / Math.PI;
      d.x = nodesPos[d.name].x / radius;
      d.y = nodesPos[d.name].y / radius;

      let incoming = [];
      d.incoming.forEach(i => {
        if (availPos.includes(i)) {
          incoming.push({
            "from": i.replaceAll(".", "--"),
            "to": d.name.replaceAll(".", "--"),
            "path": computeLine(nodesPos[d.name], nodesPos[i])
          });
        }
      });

      let outgoing = [];
      d.outgoing.forEach(o => {
        if (availPos.includes(o)) {
          outgoing.push({
            "from": d.name.replaceAll(".", "--"),
            "to": o.replaceAll(".", "--"),
            "path": computeLine(nodesPos[d.name], nodesPos[o])
          });
        }
      });

      // update the object
      d.name = d.name.replaceAll(".", "--");
      d.incoming = incoming;
      d.outgoing = outgoing;
    }

    // enrich the arc data with angle range
    for (let [i, [k, v]] of Object.entries(arcSpans).entries()) {
      arcs.push({
        "name": k,
        "path": computeArc(
          radius * 2,
          Math.min(...v) - angleArc / 3 + Math.PI / 2,
          Math.max(...v) + angleArc / 3 + Math.PI / 2
        )
      });
    }

    // svg canvas
    const svg = d3.create("svg")
      .attr("id", "wheel")
      .attr("width", width)
      .attr("height", height)
      .attr("viewBox", [-width / 2, -height / 2, width, height]);

    // draw arcs to identify sources
    if (data.length < 100) {
      const arc = svg.append("g")
        .selectAll(null)
        .data(arcs)
        .join("g")
        .append("path")
        .attr("fill", nodeColor)
        .attr("opacity", "0.25")
        .attr("stroke-linecap", "round")
        .attr("d", d => d.path);
    }

    // build the nodes
    const node = svg.append("g")
      .selectAll(null)
      .data(data)
      .join("g")
      .attr("transform", d => `rotate(${d.angle}) translate(${radius},0)`)
      .append("text")
      .attr("id", d => `node-${d.name}`)
      .attr("x", d => d.x)
      .attr("y", d => d.y)
      .attr("dx", d => d.angle <= 90 ? "5" : "-5")
      .attr("dy", fontSize / 3)
      .attr("text-anchor", d => d.angle <= 90 ? "start" : "end")
      .attr("transform", d => d.angle > 90 ? "rotate(180)" : null)
      .attr("cursor", "pointer")
      .attr("fill", nodeColor)
      .attr("font-size", fontSize)
      .text(d => d.name.split("--").pop())
      .on("click", clicked)
      .on("mouseover", overed)
      .on("mouseout", outed);

    // add some extra information if a small number of objects are shown
    if (data.length < 30) {
      const path = svg.append("g")
        .selectAll(null)
        .data(data)
        .join("g")
        .attr("transform", d => `rotate(${d.angle}) translate(${radius},0)`)
        .append("text")
        .attr("x", d => d.x)
        .attr("y", d => d.y)
        .attr("dx", d => d.angle <= 90 ? "5" : "-5")
        .attr("dy", fontSize * 1.25)
        .attr("text-anchor", d => d.angle <= 90 ? "start" : "end")
        .attr("transform", d => d.angle > 90 ? "rotate(180)" : null)
        .attr("fill", nodeColor)
        .attr("font-size", fontSize * 0.75)
        .attr("opacity", "0.75")
        .text(d => d.name.replaceAll("--", "."));
    }

    // build the links
    const link = svg.append("g")
      .selectAll(null)
      .data(data.flatMap(d => d.outgoing))
      .join("g")
      .append("path")
      .attr("id", d => `link-${d.from}-${d.to}`)
      .attr("class", d => `from-${d.from} to-${d.to}`)
      .attr("fill", "none")
      .attr("opacity", "0.5")
      .attr("stroke", linkColor)
      .attr("stroke-linecap", "round")
      .attr("d", d => d.path);

    // this function is called when a node is clicked; usefull for debug mainly
    function clicked(e, d) {
      const [db, sc, ob] = d.name.split("--");

      // dump
      console.log({
        "database": db,
        "schema": sc,
        "name": ob,
        "path": `${db}.${sc}.${ob}`,
        "type": d.type.toLowerCase()
      });

      // update the filter value
      filterField.value = `${db}.${sc}.${ob}`;
      form.submit()
    }

    // this function is called when the mouse hovers an object and will highlight
    // the latter, but also the immediate parents/childrens of the object
    function overed(e, d) {
      d3.select(this)
        .attr("font-size", "normal")
        .attr("font-weight", "bold")
        .raise();

      // links
      d.incoming.map(d => {
        d3.select(`#link-${d.from}-${d.to}`)
          .attr("opacity", "1.0")
          .attr("stroke", linkColorIncoming)
          .attr("stroke-width", "4")
          .select(function() { return this.parentNode; })
          .raise();
      });
      d.outgoing.map(d => {
        d3.select(`#link-${d.from}-${d.to}`)
          .attr("opacity", "1.0")
          .attr("stroke", linkColorOutgoing)
          .attr("stroke-width", "4")
          .select(function() { return this.parentNode; })
          .raise();
      });

      // nodes
      d.incoming.map(d => {
        d3.select(`#node-${d.from}`)
          .attr("fill", linkColorIncoming)
          .attr("font-size", "normal")
          .attr("font-weight", "bold")
          .raise();
      });
      d.outgoing.map(d => {
        d3.select(`#node-${d.to}`)
          .attr("fill", linkColorOutgoing)
          .attr("font-size", "normal")
          .attr("font-weight", "bold")
          .raise();
      });

    }

    // this function is called when the mouse hovers *out* of an object, cleaning up
    // all the highlights; links seem to be capricious, so we make sure *all*
    // related links are back to normal
    function outed(e, d) {
      d3.select(this)
        .attr("font-size", fontSize)
        .attr("font-weight", null);

      // links
      d.incoming.map(d => {
        d3.selectAll(`.from-${d.from}`)
          .attr("opacity", "0.5")
          .attr("stroke", linkColor)
          .attr("stroke-width", "1");
      });
      d.outgoing.map(d => {
        d3.selectAll(`.from-${d.from}`)
          .attr("opacity", "0.5")
          .attr("stroke", linkColor)
          .attr("stroke-width", "1");
      });

      // nodes
      d.incoming.map(d => {
        d3.select(`#node-${d.from}`)
          .attr("fill", nodeColor)
          .attr("font-size", fontSize)
          .attr("font-weight", "normal");
      });
      d.outgoing.map(d => {
        d3.select(`#node-${d.to}`)
          .attr("fill", nodeColor)
          .attr("font-size", fontSize)
          .attr("font-weight", "normal");
      });

    }

    return svg.node();
  }

  // filter the data, returning all related nodes according to the desired depths
  const filterData = (data, object = "", hidden = {}, nParents = -9, nChildren = +9) => {

    // filtering necessary
    if (object !== "") {
      const filteredData = [],
            indexedData = {},
            family = [];

      // index the data to ease bookkeeping
      for (let d of data) indexedData[d.name] = d;

      // fetch the whole family
      family.concat(listObjects(indexedData, object, nParents, family)); // parents
      family.concat(listObjects(indexedData, object, nChildren, family)); // children

      // exclude unwanted types on the way
      family.sort().forEach(o => {
        if (Object.keys(hidden).length !== 0) {
          let push = true;
          for (const [attrName, hiddenValues] of Object.entries(hidden)) {
            if (hiddenValues.includes(indexedData[o][attrName].toLowerCase())) push = false;
          }
          if (push) filteredData.push(indexedData[o]);
        } else {
          filteredData.push(indexedData[o]);
        }
      });

      return filteredData;

    // excluding necessary
    } else if (Object.keys(hidden).length !== 0) {
      const filteredData = [];

      // exclude unwanted
      for (let d of data) {
        let push = true;
        for (const [attrName, hiddenValues] of Object.entries(hidden)) {
          if (hiddenValues.includes(d[attrName].toLowerCase())) push = false;
        }
        if (push) filteredData.push(d);
      }

      return filteredData;

    // no filtering, nothing to do, show everything
    } else {
      return data;

    }

  }

  // create the index for the autocomplete capabilities: simply allow users to
  // search for objects from any database/schema/object name
  const indexData = (data) => {
    const index = {},
          distinctAttributes = {"database": [], "schema": [], "type": []};

    // object short name -> full path to the object
    for (let d of data) {
      let db = d.database,
          sc = d.schema,
          ob = d.name.split(".")[2];

      // short/long names -> long name
      for (let i of [`${db}.${ob}`, `${db}.${sc}.${ob}`]) {
        if (!Object.keys(index).includes(i)) index[i] = d.name;
      }

      // store distinct values for a bunch of [hardcoded] attributes
      if (!distinctAttributes.database.includes(db)) {
        distinctAttributes.database.push(db);
      }
      if (!distinctAttributes.schema.includes(`${db}.${sc}`)) {
        distinctAttributes.schema.push(`${db}.${sc}`);
      }
      if (!distinctAttributes.type.includes(d.type.toLowerCase())) {
        distinctAttributes.type.push(d.type.toLowerCase());
      }

    }

    distinctAttributes.database.sort();
    distinctAttributes.schema.sort();
    distinctAttributes.type.sort();

    return [index, Object.keys(index), distinctAttributes];
  }

  // recursively traverse the dependency graph to a certain depth
  const listObjects = (indexedData, object, depth, visited) => {
    if (!visited.includes(object)) visited.push(object);

    // parents
    if (depth < 0) {
      indexedData[object].incoming.forEach(i => {
        listObjects(indexedData, i, depth + 1, visited)
      });
    }

    // children
    if (depth > 0) {
      indexedData[object].outgoing.forEach(o => {
        listObjects(indexedData, o, depth - 1, visited)
      });
    }

    return visited;
  }

  // parse all checkboxes and extract hidden attributes/objects
  const parseCheckboxes = (checkboxes) => {
    const hiddenObjects = {};

    for (let c of checkboxes) {
      if (!c.checked) {
        const type = c.id.split("---")[0],
              value = c.id.split("---")[1].replace("--", " ");
        try {
          hiddenObjects[type].push(value);
        } catch {
          hiddenObjects[type] = [value];
        };
      }
    }

    return hiddenObjects;
  }

  // suggest the first five objects starting with the filter value
  const suggestObjects = (indexedValues, filterValue) => {
    suggestionField.innerHTML = "";
    if (filterValue !== "") {
      indexedValues.filter(o => {
        return o.toLowerCase().startsWith(filterValue.toLowerCase());
      }).slice(0, 5).forEach(s => suggestionField.innerHTML += `<li>${s}</li>`);
    }
  }

  // update button visibility according to current value
  const updateButtonVisibility = (filterValue) => {
    if (filterValue === "") {
      resetButton.style.display = "none";
    } else {
      resetButton.style.display = "block";
    }
  }

  // update local storage with current value
  const updateLocalStorage = (filterValue, hiddenObjects) => {
    if (filterValue === "") {
      localStorage.removeItem(localStorageFilterItemName);
    } else {
      localStorage.setItem(localStorageFilterItemName, filterValue);
    }
    if (hiddenObjects.length === 0) {
      localStorage.removeItem(localStorageHiddenItemName);
    } else {
      localStorage.setItem(
        localStorageHiddenItemName, JSON.stringify(hiddenObjects)
      );
    }
  }

  // list various source objects
  const updateCheckboxes = (attributes, visibleAttributeTypes, hiddenObjects = {}) => {
    visibleAttributeTypes.forEach(type => {
      if (checkboxField.innerHTML !== "") checkboxField.innerHTML += `<br><br>`;
      attributes[type].forEach(value => {
        let checked = "checked";
        if (type in hiddenObjects && hiddenObjects[type].includes(value)) checked = "";

        checkboxField.innerHTML += `
          <li>
            <label>
              <input
                id="${type}---${value.replaceAll(" ", "--")}"
                name="checkbox"
                type="checkbox"
                ${checked}
              >
              <span class="slider"></span>
              <span class="label">${value}</span>
            </label>
          </li>
        `
      });
    });
  }

  // redraw the wheel
  const updateWheel = (data, index, indexedValues, filterValue, hiddenObjects = {}) => {
    if (document.contains(document.getElementById("wheel"))) {
      document.getElementById("wheel").remove();
    }
    const filteredData = filterData(data, index[filterValue], hiddenObjects);
    if (filteredData.length > 0) {
      document.body.appendChild(
        drawDependencyWheel(
          structuredClone(filteredData),
          {
            nodeColor: computedStyle.getPropertyValue("--font-color"),
            linkColor: computedStyle.getPropertyValue("--font-color"),
            linkColorIncoming: computedStyle.getPropertyValue("--link-color"),
            width: window.innerWidth - 10,
            height: window.innerHeight - 10
          }
        )
      )
    }
  }

  const computedStyle = getComputedStyle(document.documentElement),
        localStorageFilterItemName = "lineage-wheel-filter",
        localStorageHiddenItemName = "lineage-wheel-hidden";

  const form = document.forms[0],
        filterField = form.elements[0],
        filterValue = localStorage.getItem(localStorageFilterItemName) || "",
        hiddenObjects = JSON.parse(localStorage.getItem(localStorageHiddenItemName)) || {},
        resetButton = form.elements[2];

  const checkboxField = document.getElementById("checkboxes"),
        checkboxes = document.getElementsByName("checkbox"),
        suggestionField = document.getElementById("suggestions");

  const [index, indexedValues, distinctAttributes] = indexData(rawData);

  // initial setup
  if (filterValue !== "") filterField.value = filterValue;
  updateButtonVisibility(filterValue);
  updateCheckboxes(distinctAttributes, ["database", "type"], hiddenObjects);
  updateWheel(rawData, index, indexedValues, filterValue, hiddenObjects);

  // event listener: completion on key press
  filterField.onkeypress = () => {
    suggestObjects(indexedValues, filterField.value);
  }

  // event listener: update wheel once a checkbox is clicked
  checkboxField.onclick = () => {
    const hiddenObjects = parseCheckboxes(checkboxes);
    updateLocalStorage(filterField.value, hiddenObjects);
    updateWheel(rawData, index, indexedValues, filterField.value, hiddenObjects);
  }

  // event listener: update wheel once a suggestion is clicked
  suggestionField.onclick = ({target}) => {
    if (target.tagName === "LI") {
      filterField.value = target.textContent;
      form.submit();
    }
  }

  // event listener: update wheel on form submission
  form.submit = () => {
    suggestionField.innerHTML = "";
    const hiddenObjects = parseCheckboxes(checkboxes);
    updateButtonVisibility(filterField.value);
    updateLocalStorage(filterField.value, hiddenObjects);
    updateWheel(rawData, index, indexedValues, filterField.value, hiddenObjects);
  }

  // event listener: reset filters and update wheel
  form.onreset = () => {
    filterField.value = "";
    resetButton.style.display = "none";
    form.submit();
  }

});
